"""Identity test fixture factories.

Purpose:
    Provide small domain-model factories for user and profile tests.

Relationships:
    - Unit web tests use these helpers to keep auth and profile setup compact.
    - Application tests rely on the same domain models as production handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

import pytest

from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile


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
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_user_profile(
    *,
    user_id: UUID,
    allow_remote_fallback: bool | None = None,
    inline_completion_provider: Literal["local", "external"] | None = None,
    classroom_planner_smart_enabled: bool | None = None,
    classroom_planner_use_history: bool | None = None,
    classroom_planner_grouping_seating_distance_enabled: bool | None = None,
    now: datetime | None = None,
) -> UserProfile:
    ts = now or datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return UserProfile(
        user_id=user_id,
        first_name=None,
        last_name=None,
        display_name=None,
        allow_remote_fallback=allow_remote_fallback,
        inline_completion_provider=inline_completion_provider,
        classroom_planner_smart_enabled=classroom_planner_smart_enabled,
        classroom_planner_use_history=classroom_planner_use_history,
        classroom_planner_grouping_seating_distance_enabled=(
            classroom_planner_grouping_seating_distance_enabled
        ),
        locale="sv-SE",
        created_at=ts,
        updated_at=ts,
    )
