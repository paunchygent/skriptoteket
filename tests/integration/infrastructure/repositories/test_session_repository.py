from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, Session
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.session_repository import (
    PostgreSQLSessionRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
async def user_id(db_session: AsyncSession, now: datetime) -> UUID:
    """Create a user for session FK constraint."""
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"session-test-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


@pytest.mark.integration
async def test_session_create_and_get(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLSessionRepository(db_session)

    session_id = uuid4()
    expires_at = now + timedelta(hours=24)

    session = Session(
        id=session_id,
        user_id=user_id,
        csrf_token="csrf-token-abc123",
        created_at=now,
        expires_at=expires_at,
        revoked_at=None,
    )

    # Create
    await repo.create(session=session)

    # Get
    fetched = await repo.get_by_id(session_id)
    assert fetched is not None
    assert fetched.id == session_id
    assert fetched.user_id == user_id
    assert fetched.csrf_token == "csrf-token-abc123"
    assert fetched.expires_at == expires_at
    assert fetched.revoked_at is None


@pytest.mark.integration
async def test_session_revoke(db_session: AsyncSession, user_id: UUID, now: datetime) -> None:
    repo = PostgreSQLSessionRepository(db_session)

    session_id = uuid4()
    session = Session(
        id=session_id,
        user_id=user_id,
        csrf_token="to-be-revoked",
        created_at=now,
        expires_at=now + timedelta(hours=24),
        revoked_at=None,
    )
    await repo.create(session=session)

    # Verify not revoked
    fetched = await repo.get_by_id(session_id)
    assert fetched is not None
    assert fetched.revoked_at is None

    # Revoke
    await repo.revoke(session_id=session_id)

    # Verify revoked
    fetched_after = await repo.get_by_id(session_id)
    assert fetched_after is not None
    assert fetched_after.revoked_at is not None


@pytest.mark.integration
async def test_session_get_nonexistent(db_session: AsyncSession) -> None:
    repo = PostgreSQLSessionRepository(db_session)

    fetched = await repo.get_by_id(uuid4())
    assert fetched is None
