from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import UserProfile
from skriptoteket.infrastructure.db.models.user_profile import UserProfileModel
from skriptoteket.protocols.identity import ProfileRepositoryProtocol


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
            locale=profile.locale,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return UserProfile.model_validate(model)

    async def update(self, *, profile: UserProfile) -> UserProfile:
        model = await self._session.get(UserProfileModel, profile.user_id)
        if model is None:
            raise not_found("UserProfile", str(profile.user_id))

        model.first_name = profile.first_name
        model.last_name = profile.last_name
        model.display_name = profile.display_name
        model.locale = profile.locale
        model.updated_at = profile.updated_at

        await self._session.flush()
        await self._session.refresh(model)
        return UserProfile.model_validate(model)
