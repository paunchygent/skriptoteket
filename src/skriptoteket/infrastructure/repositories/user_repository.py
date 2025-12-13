from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import User, UserAuth
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.protocols.identity import UserRepositoryProtocol


class PostgreSQLUserRepository(UserRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return User.model_validate(model) if model else None

    async def get_auth_by_email(self, email: str) -> UserAuth | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        if not model:
            return None
        user = User.model_validate(model)
        return UserAuth(user=user, password_hash=model.password_hash)

    async def create(self, *, user: User, password_hash: str | None) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            role=user.role.value,
            auth_provider=user.auth_provider.value,
            external_id=user.external_id,
            password_hash=password_hash,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return User.model_validate(model)
