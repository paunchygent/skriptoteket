"""Actor builder shared by the exam workspace suggestion tests.

Purpose:
    Build the signed-in teacher the workspace suggestion handler tests act as.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from skriptoteket.domain.identity.models import AuthProvider, Role, User

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


def make_actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
        email_verified=True,
        created_at=NOW,
        updated_at=NOW,
    )
