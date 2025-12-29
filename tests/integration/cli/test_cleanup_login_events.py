from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.cli.commands.cleanup_login_events import _cleanup_login_events_async
from skriptoteket.domain.identity.login_events import LoginEvent, LoginEventStatus
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.repositories.login_event_repository import (
    PostgreSQLLoginEventRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(*, db_session: AsyncSession, now: datetime) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"cleanup-{uuid.uuid4().hex[:6]}@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    users = PostgreSQLUserRepository(db_session)
    return await users.create(user=user, password_hash="hash")


@pytest.mark.integration
async def test_cleanup_login_events_command_deletes_expired(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    user = await _create_user(db_session=db_session, now=now)
    repo = PostgreSQLLoginEventRepository(db_session)

    expired_event = LoginEvent(
        id=uuid.uuid4(),
        user_id=user.id,
        status=LoginEventStatus.FAILURE,
        failure_code="INVALID_CREDENTIALS",
        ip_address="127.0.0.1",
        user_agent="pytest",
        auth_provider=AuthProvider.LOCAL,
        correlation_id=uuid.uuid4(),
        geo_country_code=None,
        geo_region=None,
        geo_city=None,
        geo_latitude=None,
        geo_longitude=None,
        created_at=now - timedelta(days=120),
    )
    active_event = LoginEvent(
        id=uuid.uuid4(),
        user_id=user.id,
        status=LoginEventStatus.SUCCESS,
        failure_code=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
        auth_provider=AuthProvider.LOCAL,
        correlation_id=uuid.uuid4(),
        geo_country_code=None,
        geo_region=None,
        geo_city=None,
        geo_latitude=None,
        geo_longitude=None,
        created_at=now - timedelta(days=5),
    )

    await repo.create(event=expired_event)
    await repo.create(event=active_event)
    await db_session.commit()

    monkeypatch.setenv("DATABASE_URL", database_url)

    await _cleanup_login_events_async()

    async with session_factory() as session:
        check_repo = PostgreSQLLoginEventRepository(session)
        remaining = await check_repo.list_by_user(user_id=user.id, limit=10)
        assert len(remaining) == 1
        assert remaining[0].id == active_event.id
