"""Shared fixtures for sandbox handler tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol


@pytest.fixture
def session_files() -> AsyncMock:
    storage = AsyncMock(spec=SessionFileStorageProtocol)
    storage.get_files.return_value = []
    return storage


@pytest.fixture
def locks() -> AsyncMock:
    return AsyncMock(spec=DraftLockRepositoryProtocol)


@pytest.fixture
def clock(now: datetime) -> Mock:
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    return clock


@pytest.fixture
def snapshots() -> AsyncMock:
    return AsyncMock(spec=SandboxSnapshotRepositoryProtocol)
