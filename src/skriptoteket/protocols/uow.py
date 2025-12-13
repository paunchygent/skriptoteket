from __future__ import annotations

from typing import Protocol


class UnitOfWorkProtocol(Protocol):
    async def __aenter__(self) -> "UnitOfWorkProtocol": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
