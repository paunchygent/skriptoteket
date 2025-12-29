from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot


class SandboxSnapshotRepositoryProtocol(Protocol):
    async def get_by_id(self, *, snapshot_id: UUID) -> SandboxSnapshot | None: ...

    async def create(self, *, snapshot: SandboxSnapshot) -> SandboxSnapshot: ...

    async def delete_expired(self, *, now: datetime) -> int: ...
