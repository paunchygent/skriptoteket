from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User


@pytest.fixture
def now() -> datetime:
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_user(
    *, role: Role = Role.USER, email: str = "user@example.com", user_id: UUID | None = None
) -> User:
    timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        role=role,
        auth_provider=AuthProvider.LOCAL,
        external_id=None,
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_session(
    *,
    session_id: UUID | None = None,
    user_id: UUID,
    now: datetime | None = None,
    expires_in: timedelta = timedelta(hours=1),
    revoked: bool = False,
) -> Session:
    ts = now or datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return Session(
        id=session_id or uuid4(),
        user_id=user_id,
        csrf_token="csrf-token",
        created_at=ts,
        expires_at=ts + expires_in,
        revoked_at=ts if revoked else None,
    )
