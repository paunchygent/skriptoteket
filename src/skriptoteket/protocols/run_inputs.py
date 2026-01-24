from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile


class RunInputStorageProtocol(Protocol):
    async def store(
        self,
        *,
        run_id: UUID,
        files: list[ResolvedInputFile],
    ) -> None: ...

    async def get(self, *, run_id: UUID) -> list[ResolvedInputFile]: ...

    async def delete(self, *, run_id: UUID) -> None: ...
