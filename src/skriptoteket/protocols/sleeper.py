from __future__ import annotations

from typing import Protocol


class SleeperProtocol(Protocol):
    async def sleep(self, seconds: float) -> None: ...
