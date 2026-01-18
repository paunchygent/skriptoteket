from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.protocols.session_files import InputFile


class RunInputStorageProtocol(Protocol):
    async def store(
        self,
        *,
        run_id: UUID,
        files: list[InputFile],
    ) -> None: ...

    async def get(self, *, run_id: UUID) -> list[InputFile]: ...

    async def delete(self, *, run_id: UUID) -> None: ...
