from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.draft_locks import (
    AcquireDraftLockCommand,
    ReleaseDraftLockCommand,
)
from skriptoteket.application.scripting.handlers.acquire_draft_lock import (
    AcquireDraftLockHandler,
)
from skriptoteket.application.scripting.handlers.release_draft_lock import (
    ReleaseDraftLockHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import FakeUow


def _make_lock(
    *,
    tool_id,
    draft_head_id,
    locked_by_user_id,
    now: datetime,
    expires_in: timedelta,
    forced_by_user_id=None,
) -> DraftLock:
    return DraftLock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=locked_by_user_id,
        locked_at=now,
        expires_at=now + expires_in,
        forced_by_user_id=forced_by_user_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_draft_lock_creates_new_lock(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    draft_head_id = uuid4()

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = None

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    saved_lock = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=actor.id,
        now=now,
        expires_in=timedelta(seconds=settings.DRAFT_LOCK_TTL_SECONDS),
    )
    locks.upsert.return_value = saved_lock

    handler = AcquireDraftLockHandler(
        settings=settings,
        uow=uow,
        locks=locks,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        command=AcquireDraftLockCommand(tool_id=tool_id, draft_head_id=draft_head_id),
    )

    assert result.tool_id == tool_id
    assert result.draft_head_id == draft_head_id
    assert result.locked_by_user_id == actor.id
    assert result.expires_at == saved_lock.expires_at
    assert result.is_owner is True
    locks.upsert.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_draft_lock_rejects_other_user_without_force(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    other_user_id = uuid4()
    tool_id = uuid4()
    draft_head_id = uuid4()

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=other_user_id,
        now=now,
        expires_in=timedelta(minutes=5),
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = AcquireDraftLockHandler(
        settings=settings,
        uow=uow,
        locks=locks,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AcquireDraftLockCommand(tool_id=tool_id, draft_head_id=draft_head_id),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    locks.upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_draft_lock_force_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    other_user_id = uuid4()
    tool_id = uuid4()
    draft_head_id = uuid4()

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=other_user_id,
        now=now,
        expires_in=timedelta(minutes=5),
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = AcquireDraftLockHandler(
        settings=settings,
        uow=uow,
        locks=locks,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AcquireDraftLockCommand(
                tool_id=tool_id,
                draft_head_id=draft_head_id,
                force=True,
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    locks.upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_draft_lock_force_by_admin_sets_forced_by_user_id(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN)
    other_user_id = uuid4()
    tool_id = uuid4()
    draft_head_id = uuid4()

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=other_user_id,
        now=now,
        expires_in=timedelta(minutes=5),
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    updated_lock = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=actor.id,
        now=now,
        expires_in=timedelta(seconds=settings.DRAFT_LOCK_TTL_SECONDS),
        forced_by_user_id=actor.id,
    )
    locks.upsert.return_value = updated_lock

    handler = AcquireDraftLockHandler(
        settings=settings,
        uow=uow,
        locks=locks,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        command=AcquireDraftLockCommand(
            tool_id=tool_id,
            draft_head_id=draft_head_id,
            force=True,
        ),
    )

    assert result.is_owner is True
    saved_lock = locks.upsert.call_args.kwargs["lock"]
    assert saved_lock.forced_by_user_id == actor.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_draft_lock_allows_expired_lock(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    draft_head_id = uuid4()

    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=uuid4(),
        now=now - timedelta(minutes=20),
        expires_in=timedelta(minutes=-1),
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    saved_lock = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=actor.id,
        now=now,
        expires_in=timedelta(seconds=settings.DRAFT_LOCK_TTL_SECONDS),
    )
    locks.upsert.return_value = saved_lock

    handler = AcquireDraftLockHandler(
        settings=settings,
        uow=uow,
        locks=locks,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        command=AcquireDraftLockCommand(tool_id=tool_id, draft_head_id=draft_head_id),
    )

    assert result.is_owner is True
    locks.upsert.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_draft_lock_deletes_for_owner(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    draft_head_id = uuid4()

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=actor.id,
        now=now,
        expires_in=timedelta(minutes=5),
    )

    handler = ReleaseDraftLockHandler(uow=uow, locks=locks)

    result = await handler.handle(
        actor=actor,
        command=ReleaseDraftLockCommand(tool_id=tool_id),
    )

    assert result.tool_id == tool_id
    locks.delete.assert_awaited_once_with(tool_id=tool_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_draft_lock_rejects_other_user(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    other_user_id = uuid4()
    tool_id = uuid4()
    draft_head_id = uuid4()

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=other_user_id,
        now=now,
        expires_in=timedelta(minutes=5),
    )

    handler = ReleaseDraftLockHandler(uow=uow, locks=locks)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=ReleaseDraftLockCommand(tool_id=tool_id),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    locks.delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_draft_lock_allows_admin_override(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    other_user_id = uuid4()
    tool_id = uuid4()
    draft_head_id = uuid4()

    uow = FakeUow()
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=other_user_id,
        now=now,
        expires_in=timedelta(minutes=5),
    )

    handler = ReleaseDraftLockHandler(uow=uow, locks=locks)

    result = await handler.handle(
        actor=actor,
        command=ReleaseDraftLockCommand(tool_id=tool_id),
    )

    assert result.tool_id == tool_id
    locks.delete.assert_awaited_once_with(tool_id=tool_id)
