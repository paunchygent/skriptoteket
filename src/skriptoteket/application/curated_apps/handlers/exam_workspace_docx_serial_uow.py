"""One request unit of work shared by concurrent conversion tasks, one transaction at a time.

Type batches and labeling calls run concurrently, but their token-lease reservations,
reconciliations and progress writes share the request's unit of work. Each transaction
holds ``lock`` from enter to exit; provider calls run outside it.
"""

from __future__ import annotations

import asyncio
from types import TracebackType

from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SerializedUnitOfWork(UnitOfWorkProtocol):
    """Enter the wrapped unit of work only while holding the shared lock."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow
        self.lock = asyncio.Lock()

    async def __aenter__(self) -> SerializedUnitOfWork:
        await self.lock.acquire()
        try:
            await self._uow.__aenter__()
        except BaseException:
            self.lock.release()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await self._uow.__aexit__(exc_type, exc, tb)
        finally:
            self.lock.release()
