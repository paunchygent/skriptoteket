from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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


@pytest.mark.integration
async def test_user_update(db_session: AsyncSession) -> None:
    """Test that update() persists all mutable fields including security fields."""
    repo = PostgreSQLUserRepository(db_session)

    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    later = now + timedelta(hours=1)
    lock_until = now + timedelta(hours=24)

    # Create user with defaults
    user = User(
        id=user_id,
        email="update-test@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        email_verified=False,
        failed_login_attempts=0,
        created_at=now,
        updated_at=now,
    )
    await repo.create(user=user, password_hash="initial_hash")

    # Update all mutable fields
    updated_user = user.model_copy(
        update={
            "email": "new-email@example.com",
            "role": Role.CONTRIBUTOR,
            "auth_provider": AuthProvider.HULEEDU,
            "external_id": "ext-123",
            "is_active": False,
            "email_verified": True,
            "failed_login_attempts": 3,
            "locked_until": lock_until,
            "last_login_at": now,
            "last_failed_login_at": later,
            "updated_at": later,
        }
    )
    result = await repo.update(user=updated_user)

    assert result.email == "new-email@example.com"
    assert result.role == Role.CONTRIBUTOR
    assert result.auth_provider == AuthProvider.HULEEDU
    assert result.external_id == "ext-123"
    assert result.is_active is False
    assert result.email_verified is True
    assert result.failed_login_attempts == 3
    assert result.locked_until == lock_until
    assert result.last_login_at == now
    assert result.last_failed_login_at == later

    # Verify persistence
    fetched = await repo.get_by_id(user_id)
    assert fetched is not None
    assert fetched.email == "new-email@example.com"
    assert fetched.role == Role.CONTRIBUTOR
    assert fetched.external_id == "ext-123"
    assert fetched.is_active is False
    assert fetched.email_verified is True
    assert fetched.failed_login_attempts == 3
    assert fetched.locked_until == lock_until


@pytest.mark.integration
async def test_user_update_password_hash(db_session: AsyncSession) -> None:
    """Test that update_password_hash() persists the new password hash."""
    repo = PostgreSQLUserRepository(db_session)

    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    later = now + timedelta(hours=1)

    user = User(
        id=user_id,
        email="password-test@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    await repo.create(user=user, password_hash="old_hash")

    # Update password hash
    await repo.update_password_hash(
        user_id=user_id,
        password_hash="new_secure_hash",
        updated_at=later,
    )

    # Verify via get_auth_by_email
    auth = await repo.get_auth_by_email("password-test@example.com")
    assert auth is not None
    assert auth.password_hash == "new_secure_hash"


@pytest.mark.integration
async def test_user_update_raises_not_found(db_session: AsyncSession) -> None:
    """Test that update() raises NOT_FOUND for missing user."""
    from skriptoteket.domain.errors import DomainError, ErrorCode

    repo = PostgreSQLUserRepository(db_session)
    now = datetime.now(timezone.utc)

    missing_user = User(
        id=uuid.uuid4(),
        email="ghost@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(DomainError) as exc:
        await repo.update(user=missing_user)
    assert exc.value.code == ErrorCode.NOT_FOUND
