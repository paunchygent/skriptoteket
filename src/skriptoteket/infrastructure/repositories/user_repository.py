from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User, UserAuth
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.protocols.identity import UserRepositoryProtocol


class PostgreSQLUserRepository(UserRepositoryProtocol):
    """PostgreSQL repository for users and authentication data.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

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
            email_verified=user.email_verified,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            last_login_at=user.last_login_at,
            last_failed_login_at=user.last_failed_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return User.model_validate(model)

    async def update(self, *, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            raise not_found("User", str(user.id))

        model.email = user.email
        model.role = user.role.value
        model.auth_provider = user.auth_provider.value
        model.external_id = user.external_id
        model.is_active = user.is_active
        model.email_verified = user.email_verified
        model.failed_login_attempts = user.failed_login_attempts
        model.locked_until = user.locked_until
        model.last_login_at = user.last_login_at
        model.last_failed_login_at = user.last_failed_login_at
        model.updated_at = user.updated_at

        await self._session.flush()
        await self._session.refresh(model)
        return User.model_validate(model)

    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, updated_at: datetime
    ) -> None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            raise not_found("User", str(user_id))

        model.password_hash = password_hash
        model.updated_at = updated_at
        await self._session.flush()

    async def count_active_by_role(self) -> dict[Role, int]:
        stmt = (
            select(UserModel.role, func.count())
            .where(UserModel.is_active.is_(True))
            .group_by(UserModel.role)
        )
        result = await self._session.execute(stmt)
        counts: dict[Role, int] = {}
        for role_value, count in result.all():
            try:
                role = Role(role_value)
            except ValueError:
                continue
            counts[role] = int(count)
        return counts

    async def list_users(self, *, limit: int, offset: int) -> list[User]:
        stmt = select(UserModel).order_by(UserModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [User.model_validate(model) for model in result.scalars().all()]

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(UserModel))
        return int(result.scalar_one())
