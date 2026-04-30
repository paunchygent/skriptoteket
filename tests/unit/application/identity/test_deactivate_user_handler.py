"""Tests for superuser account deactivation lifecycle handling.

Purpose:
    Prove user deactivation revokes Klassrumskartan owner shares before the
    account state changes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.identity.admin_users import DeactivateUserCommand
from skriptoteket.application.identity.handlers.deactivate_user import DeactivateUserHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User


class _FakeUow:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def __aenter__(self) -> _FakeUow:
        self._events.append("uow-enter")
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._events.append("uow-exit")


class _FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _FakeUsers:
    def __init__(self, *, user: User, events: list[str]) -> None:
        self.user = user
        self.updated_user: User | None = None
        self._events = events

    async def get_by_id(self, user_id: UUID) -> User | None:
        self._events.append("get-user")
        return self.user if self.user.id == user_id else None

    async def update(self, *, user: User) -> User:
        self._events.append("user-update")
        self.updated_user = user
        self.user = user
        return user

    async def count_active_by_role(self) -> dict[Role, int]:
        self._events.append("count-active")
        return {Role.SUPERUSER: 1}


class _FakeShareLifecycle:
    def __init__(self, events: list[str]) -> None:
        self.owner_user_id: UUID | None = None
        self._events = events

    async def revoke_for_owner_delete(self, *, owner_user_id: UUID) -> int:
        self._events.append("shares-revoked")
        self.owner_user_id = owner_user_id
        return 3


def _user(*, role: Role, is_active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        email=f"{role.value}-{uuid4()}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        is_active=is_active,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deactivate_user_revokes_owned_share_artifacts_before_state_change() -> None:
    events: list[str] = []
    target = _user(role=Role.USER)
    now = datetime.now(timezone.utc)
    users = _FakeUsers(user=target, events=events)
    share_lifecycle = _FakeShareLifecycle(events=events)
    handler = DeactivateUserHandler(
        uow=_FakeUow(events),
        users=users,
        share_lifecycle=share_lifecycle,
        clock=_FakeClock(now),
    )

    result = await handler.handle(
        actor=_user(role=Role.SUPERUSER),
        command=DeactivateUserCommand(user_id=target.id),
    )

    assert events == ["uow-enter", "get-user", "shares-revoked", "user-update", "uow-exit"]
    assert share_lifecycle.owner_user_id == target.id
    assert result.share_artifacts_revoked == 3
    assert result.user.is_active is False
    assert result.user.updated_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deactivate_user_rejects_last_active_superuser_before_share_revocation() -> None:
    events: list[str] = []
    target = _user(role=Role.SUPERUSER)
    handler = DeactivateUserHandler(
        uow=_FakeUow(events),
        users=_FakeUsers(user=target, events=events),
        share_lifecycle=_FakeShareLifecycle(events=events),
        clock=_FakeClock(datetime.now(timezone.utc)),
    )

    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_user(role=Role.SUPERUSER),
            command=DeactivateUserCommand(user_id=target.id),
        )

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert events == ["uow-enter", "get-user", "count-active", "uow-exit"]
