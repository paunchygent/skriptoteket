from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.db.models.user import UserModel


async def create_owner(
    session_factory: async_sessionmaker[AsyncSession], role: Role = Role.USER
) -> User:
    owner_id = uuid4()
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        session.add(
            UserModel(
                id=owner_id,
                email=f"exam-workspace-{owner_id}@example.test",
                password_hash="hash",
                role=role,
                auth_provider=AuthProvider.LOCAL,
                created_at=now,
                updated_at=now,
            )
        )
    return User(
        id=owner_id,
        email=f"exam-workspace-{owner_id}@example.test",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
