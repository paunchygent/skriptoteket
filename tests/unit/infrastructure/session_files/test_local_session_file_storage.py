from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.session_files.local_session_file_storage import (
    LocalSessionFileStorage,
)
from skriptoteket.protocols.clock import ClockProtocol


class FakeClock(ClockProtocol):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_and_get_files_updates_last_accessed_at(tmp_path) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    clock = FakeClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
    storage = LocalSessionFileStorage(sessions_root=tmp_path, ttl_seconds=60, clock=clock)

    await storage.store_files(
        tool_id=tool_id,
        user_id=user_id,
        context="default",
        files=[("input.txt", b"hello")],
    )

    session_dir = next((tmp_path / "sessions" / str(tool_id) / str(user_id)).iterdir())
    meta_path = session_dir / "meta.json"
    assert meta_path.exists()
    assert meta_path.read_text("utf-8").find("last_accessed_at") != -1

    clock.advance(timedelta(seconds=10))
    files = await storage.get_files(tool_id=tool_id, user_id=user_id, context="default")
    assert files == [("input.txt", b"hello")]

    meta_after = meta_path.read_text("utf-8")
    assert clock.now().isoformat() in meta_after


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_files_replaces_existing_session_files(tmp_path) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    clock = FakeClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
    storage = LocalSessionFileStorage(sessions_root=tmp_path, ttl_seconds=60, clock=clock)

    await storage.store_files(
        tool_id=tool_id,
        user_id=user_id,
        context="default",
        files=[("a.txt", b"a")],
    )
    await storage.store_files(
        tool_id=tool_id,
        user_id=user_id,
        context="default",
        files=[("b.txt", b"b")],
    )

    files = await storage.get_files(tool_id=tool_id, user_id=user_id, context="default")
    assert files == [("b.txt", b"b")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_files_rejects_action_json_reserved_name(tmp_path) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    clock = FakeClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
    storage = LocalSessionFileStorage(sessions_root=tmp_path, ttl_seconds=60, clock=clock)

    with pytest.raises(DomainError) as exc_info:
        await storage.store_files(
            tool_id=tool_id,
            user_id=user_id,
            context="default",
            files=[("action.json", b"{}")],
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_session_removes_files(tmp_path) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    clock = FakeClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
    storage = LocalSessionFileStorage(sessions_root=tmp_path, ttl_seconds=60, clock=clock)

    await storage.store_files(
        tool_id=tool_id,
        user_id=user_id,
        context="default",
        files=[("a.txt", b"a")],
    )
    await storage.clear_session(tool_id=tool_id, user_id=user_id, context="default")

    assert await storage.get_files(tool_id=tool_id, user_id=user_id, context="default") == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_expired_deletes_sessions_by_last_accessed_at(tmp_path) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    clock = FakeClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
    storage = LocalSessionFileStorage(sessions_root=tmp_path, ttl_seconds=5, clock=clock)

    await storage.store_files(
        tool_id=tool_id,
        user_id=user_id,
        context="default",
        files=[("a.txt", b"hello")],
    )

    clock.advance(timedelta(seconds=10))
    result = await storage.cleanup_expired()
    assert result.scanned_sessions == 1
    assert result.deleted_sessions == 1
    assert result.deleted_files == 1
    assert result.deleted_bytes == 5

    assert await storage.get_files(tool_id=tool_id, user_id=user_id, context="default") == []
