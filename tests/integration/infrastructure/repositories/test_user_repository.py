from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_user_repository_crud(db_session: AsyncSession) -> None:
    repo = PostgreSQLUserRepository(db_session)

    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Create User Domain Model
    new_user = User(
        id=user_id,
        email="test@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        external_id=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    # 1. Test Add
    await repo.create(user=new_user, password_hash="dummy_hash")

    # 2. Test Get by ID
    fetched_user = await repo.get_by_id(user_id)
    assert fetched_user is not None
    assert fetched_user.id == user_id
    assert fetched_user.email == "test@example.com"
    assert fetched_user.role == Role.USER

    # 3. Test Get by Email
    fetched_by_email = await repo.get_auth_by_email("test@example.com")
    assert fetched_by_email is not None
    assert fetched_by_email.user.id == user_id
    assert fetched_by_email.password_hash == "dummy_hash"

    # 4. Test Get Non-Existent
    missing_user = await repo.get_by_id(uuid.uuid4())
    assert missing_user is None
