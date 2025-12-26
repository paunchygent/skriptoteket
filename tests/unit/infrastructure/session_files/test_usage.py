from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.infrastructure.session_files.local_session_file_storage import (
    LocalSessionFileStorage,
)
from skriptoteket.infrastructure.session_files.usage import get_session_file_usage
from skriptoteket.protocols.clock import ClockProtocol


class FakeClock(ClockProtocol):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_session_file_usage_counts_bytes_and_files_excluding_meta_json(tmp_path) -> None:
    clock = FakeClock(datetime(2025, 1, 1, tzinfo=timezone.utc))
    storage = LocalSessionFileStorage(sessions_root=tmp_path, ttl_seconds=60, clock=clock)

    await storage.store_files(
        tool_id=uuid4(),
        user_id=uuid4(),
        context="default",
        files=[("a.txt", b"a")],
    )
    await storage.store_files(
        tool_id=uuid4(),
        user_id=uuid4(),
        context="default",
        files=[("b.txt", b"bb")],
    )

    usage = get_session_file_usage(artifacts_root=tmp_path)
    assert usage.sessions == 2
    assert usage.files == 2
    assert usage.bytes_total == 3
