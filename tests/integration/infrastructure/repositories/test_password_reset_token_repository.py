from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.identity.password_reset import (
    PasswordResetToken,
    hash_password_reset_token,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.password_reset_token_repository import (
    PostgreSQLPasswordResetTokenRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
async def user_id(db_session: AsyncSession, now: datetime) -> UUID:
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"reset-test-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            email_verified=True,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


@pytest.mark.integration
async def test_password_reset_token_create_and_get_by_hash(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLPasswordResetTokenRepository(db_session)
    token = PasswordResetToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_password_reset_token(token="reset-token"),
        expires_at=now + timedelta(hours=2),
        used_at=None,
        created_at=now,
    )

    await repo.create(token=token)

    fetched = await repo.get_by_token_hash(token_hash=token.token_hash)
    assert fetched is not None
    assert fetched.id == token.id
    assert fetched.token_hash == token.token_hash
    assert fetched.used_at is None


@pytest.mark.integration
async def test_password_reset_token_mark_used(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLPasswordResetTokenRepository(db_session)
    token = PasswordResetToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_password_reset_token(token="mark-used"),
        expires_at=now + timedelta(hours=2),
        used_at=None,
        created_at=now,
    )
    await repo.create(token=token)

    used_at = now + timedelta(minutes=5)
    await repo.mark_used(token_id=token.id, used_at=used_at)

    fetched = await repo.get_by_token_hash(token_hash=token.token_hash)
    assert fetched is not None
    assert fetched.used_at == used_at


@pytest.mark.integration
async def test_password_reset_token_second_issue_invalidates_first(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLPasswordResetTokenRepository(db_session)
    first_token = PasswordResetToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_password_reset_token(token="first-token"),
        expires_at=now + timedelta(hours=2),
        used_at=None,
        created_at=now,
    )
    await repo.create(token=first_token)

    invalidated_at = now + timedelta(minutes=10)
    invalidated_count = await repo.invalidate_pending_for_user(
        user_id=user_id,
        used_at=invalidated_at,
    )
    second_token = PasswordResetToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_password_reset_token(token="second-token"),
        expires_at=invalidated_at + timedelta(hours=2),
        used_at=None,
        created_at=invalidated_at,
    )
    await repo.create(token=second_token)

    assert invalidated_count >= 1
    first_fetched = await repo.get_by_token_hash(token_hash=first_token.token_hash)
    second_fetched = await repo.get_by_token_hash(token_hash=second_token.token_hash)
    assert first_fetched is not None and first_fetched.used_at == invalidated_at
    assert second_fetched is not None and second_fetched.used_at is None
