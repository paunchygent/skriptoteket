from __future__ import annotations

import asyncio
from uuid import UUID

from skriptoteket.protocols.llm import ChatInFlightGuardProtocol


class InProcessChatInFlightGuard(ChatInFlightGuardProtocol):
    """Best-effort, per-process single-flight guard (not for correctness)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._inflight: set[tuple[UUID, UUID]] = set()

    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool:
        async with self._lock:
            key = (user_id, tool_id)
            if key in self._inflight:
                return False
            self._inflight.add(key)
            return True

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None:
        async with self._lock:
            self._inflight.discard((user_id, tool_id))
