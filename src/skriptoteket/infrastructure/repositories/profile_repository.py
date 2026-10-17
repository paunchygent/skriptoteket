from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import UserProfile
from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel
from skriptoteket.protocols.identity import ProfileRepositoryProtocol, ProfileUpdateField


class PostgreSQLProfileRepository(ProfileRepositoryProtocol):
    """PostgreSQL repository for user profiles.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, *, user_id: UUID) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return UserProfile.model_validate(model) if model else None

    async def create(self, *, profile: UserProfile) -> UserProfile:
        model = UserProfileModel(
            user_id=profile.user_id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            display_name=profile.display_name,
            allow_remote_fallback=profile.allow_remote_fallback,
            inline_completion_provider=profile.inline_completion_provider,
            classroom_planner_smart_enabled=profile.classroom_planner_smart_enabled,
            classroom_planner_use_history=profile.classroom_planner_use_history,
            classroom_planner_grouping_seating_distance_enabled=(
                profile.classroom_planner_grouping_seating_distance_enabled
            ),
            classroom_planner_tutorial_seen_sections=(
                profile.classroom_planner_tutorial_seen_sections
            ),
            exam_courses=profile.exam_courses.model_dump(),
            locale=profile.locale,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return UserProfile.model_validate(model)

    async def update(
        self, *, profile: UserProfile, fields: frozenset[ProfileUpdateField]
    ) -> UserProfile:
        # Serialize JSONB values without assigning unrelated stale snapshot fields.
        values = profile.model_dump(include=set[str](fields))
        result = await self._session.execute(
            update(UserProfileModel)
            .where(UserProfileModel.user_id == profile.user_id)
            .values(**values)
            .returning(UserProfileModel)
            .execution_options(populate_existing=True)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise not_found("UserProfile", str(profile.user_id))
        return UserProfile.model_validate(model)
