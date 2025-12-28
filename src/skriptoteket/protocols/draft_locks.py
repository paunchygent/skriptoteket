from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.scripting.draft_locks import (
    AcquireDraftLockCommand,
    AcquireDraftLockResult,
    ReleaseDraftLockCommand,
    ReleaseDraftLockResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.draft_locks import DraftLock


class DraftLockRepositoryProtocol(Protocol):
    async def get_for_tool(self, *, tool_id: UUID) -> DraftLock | None: ...

    async def upsert(self, *, lock: DraftLock) -> DraftLock: ...

    async def delete(self, *, tool_id: UUID) -> None: ...


class AcquireDraftLockHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: AcquireDraftLockCommand,
    ) -> AcquireDraftLockResult: ...


class ReleaseDraftLockHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReleaseDraftLockCommand,
    ) -> ReleaseDraftLockResult: ...
