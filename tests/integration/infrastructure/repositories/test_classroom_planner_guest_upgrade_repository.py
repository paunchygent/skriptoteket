"""Integration tests for the classroom planner guest-upgrade repository."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.db.models.classroom_planner_guest_upgrade_consumption import (
    ClassroomPlannerGuestUpgradeConsumptionModel,
)
from skriptoteket.infrastructure.repositories.classroom_planner_guest_upgrade import (
    PostgreSQLClassroomPlannerGuestUpgradeRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(*, db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await PostgreSQLUserRepository(db_session).create(user=user, password_hash="dummy_hash")
    return user


async def _record_consumption_in_isolated_session(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    owner_user_id,
    app_id: str,
    snapshot_id: str,
    consumed_at: datetime,
    start_event: asyncio.Event,
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLClassroomPlannerGuestUpgradeRepository(session)
        await start_event.wait()
        await repo.record_upgrade_consumption(
            owner_user_id=owner_user_id,
            app_id=app_id,
            snapshot_id=snapshot_id,
            consumed_at=consumed_at,
        )
        await session.commit()


@pytest.mark.integration
async def test_guest_upgrade_repository_records_and_reads_consumption(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session=db_session)
    repo = PostgreSQLClassroomPlannerGuestUpgradeRepository(db_session)

    assert not await repo.has_consumed_upgrade(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
    )

    await repo.record_upgrade_consumption(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-1",
        consumed_at=datetime.now(timezone.utc),
    )
    await db_session.commit()

    assert await repo.has_consumed_upgrade(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
    )


@pytest.mark.integration
async def test_guest_upgrade_repository_keeps_first_consumption_fact(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session=db_session)
    repo = PostgreSQLClassroomPlannerGuestUpgradeRepository(db_session)

    await repo.record_upgrade_consumption(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-1",
        consumed_at=datetime.now(timezone.utc),
    )
    await repo.record_upgrade_consumption(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-2",
        consumed_at=datetime.now(timezone.utc),
    )
    await db_session.commit()

    assert await repo.has_consumed_upgrade(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
    )


@pytest.mark.integration
async def test_guest_upgrade_repository_handles_concurrent_duplicate_consumption_records(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(db_session=db_session)
    await db_session.commit()

    start_event = asyncio.Event()
    first_record = _record_consumption_in_isolated_session(
        session_factory=session_factory,
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-1",
        consumed_at=datetime.now(timezone.utc),
        start_event=start_event,
    )
    second_record = _record_consumption_in_isolated_session(
        session_factory=session_factory,
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-2",
        consumed_at=datetime.now(timezone.utc),
        start_event=start_event,
    )

    start_event.set()
    await asyncio.gather(first_record, second_record)

    repo = PostgreSQLClassroomPlannerGuestUpgradeRepository(db_session)
    assert await repo.has_consumed_upgrade(
        owner_user_id=user.id,
        app_id="classroom.group-seating-studio",
    )

    result = await db_session.execute(
        select(func.count())
        .select_from(ClassroomPlannerGuestUpgradeConsumptionModel)
        .where(
            ClassroomPlannerGuestUpgradeConsumptionModel.owner_user_id == user.id,
            ClassroomPlannerGuestUpgradeConsumptionModel.app_id == "classroom.group-seating-studio",
        )
    )
    assert result.scalar_one() == 1
