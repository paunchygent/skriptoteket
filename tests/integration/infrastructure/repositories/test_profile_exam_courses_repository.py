"""Real JSONB roundtrip for ordered course preferences (requires the DB lane)."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.identity.commands import (
    UpdateExamCoursesCommand,
    UpdateProfileCommand,
)
from skriptoteket.application.identity.handlers.update_exam_courses import UpdateExamCoursesHandler
from skriptoteket.application.identity.handlers.update_profile import UpdateProfileHandler
from skriptoteket.domain.identity.models import AuthProvider, Role, UserProfile
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.profile_repository import PostgreSQLProfileRepository
from skriptoteket.protocols.identity import UserRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import FixedClock

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


async def test_exam_courses_jsonb_keeps_order_and_replaces_with_empty_preferences(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"courses-{user_id}@example.test",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    preference = {
        "school_forms": ["grundskolan", "gymnasiet"],
        "course_keys": ["SVEN2000X", "GRGRMAT01/7-9", "SVESVE01"],
    }
    profile = UserProfile.model_validate(
        {"user_id": user_id, "exam_courses": preference, "created_at": now, "updated_at": now}
    )
    repository = PostgreSQLProfileRepository(db_session)
    await repository.create(profile=profile)
    db_session.expire_all()

    stored = await db_session.scalar(
        select(UserProfileModel.exam_courses).where(UserProfileModel.user_id == user_id)
    )
    assert stored == preference
    fetched = await repository.get_by_user_id(user_id=user_id)
    assert fetched is not None
    assert fetched.exam_courses.model_dump() == preference

    empty: dict[str, list[str]] = {"school_forms": [], "course_keys": []}
    replaced = UserProfile.model_validate({**fetched.model_dump(), "exam_courses": empty})
    await repository.update(profile=replaced, fields=frozenset({"exam_courses"}))
    db_session.expire_all()
    stored = await db_session.scalar(
        select(UserProfileModel.exam_courses).where(UserProfileModel.user_id == user_id)
    )
    assert stored == empty
    fetched = await repository.get_by_user_id(user_id=user_id)
    assert fetched is not None
    assert fetched.exam_courses.model_dump() == empty


@pytest.mark.parametrize("late_mutation", ["profile", "exam_courses"])
async def test_concurrent_profile_patches_preserve_both_owned_changes(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    late_mutation: str,
) -> None:
    """Pause one handler after its read; commit the other before releasing it.

    Both schedules run real writes and UoW commits in separate PostgreSQL sessions.
    The paused read is the only controlled seam; no sleeps or database mocks.
    """
    now = datetime.now(timezone.utc)
    actor = make_user()
    db_session.add(
        UserModel(
            id=actor.id,
            email=actor.email,
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    await PostgreSQLProfileRepository(db_session).create(
        profile=UserProfile(
            user_id=actor.id,
            first_name="Before",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()
    read, resume = asyncio.Event(), asyncio.Event()

    class PausedProfileRepository(PostgreSQLProfileRepository):
        async def get_by_user_id(self, *, user_id: UUID) -> UserProfile | None:
            snapshot = await super().get_by_user_id(user_id=user_id)
            read.set()
            await resume.wait()
            return snapshot

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = actor
    clock = FixedClock(now)
    async with session_factory() as late_session, session_factory() as early_session:
        late_repository = PausedProfileRepository(late_session)
        early_repository = PostgreSQLProfileRepository(early_session)
        profile_session = late_session if late_mutation == "profile" else early_session
        courses_session = late_session if late_mutation == "exam_courses" else early_session
        profile_handler = UpdateProfileHandler(
            uow=SQLAlchemyUnitOfWork(profile_session),
            users=users,
            clock=clock,
            profiles=late_repository if late_mutation == "profile" else early_repository,
        )
        courses_handler = UpdateExamCoursesHandler(
            uow=SQLAlchemyUnitOfWork(courses_session),
            users=users,
            clock=clock,
            profiles=late_repository if late_mutation == "exam_courses" else early_repository,
        )
        profile_call = profile_handler.handle(
            UpdateProfileCommand(
                user_id=actor.id,
                first_name="After",
            )
        )
        courses_call = courses_handler.handle(
            UpdateExamCoursesCommand(
                user_id=actor.id,
                school_forms=["gymnasiet"],
                course_keys=["SVESVE02"],
            )
        )
        late_call, early_call = (
            (profile_call, courses_call)
            if late_mutation == "profile"
            else (courses_call, profile_call)
        )
        pending = asyncio.create_task(late_call)
        try:
            await read.wait()
            await early_call
        finally:
            resume.set()
            await pending

    async with session_factory() as observer:
        stored = await PostgreSQLProfileRepository(observer).get_by_user_id(user_id=actor.id)
    assert stored is not None
    assert stored.first_name == "After"
    assert stored.exam_courses.course_keys == ["SVESVE02"]
    assert stored.exam_courses.school_forms == ["gymnasiet"]
