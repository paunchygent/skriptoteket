from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.file_refs import FileRef
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile


class FileRefEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: FileRef
    name: str
    bytes: int


class FileRefResolverProtocol(Protocol):
    async def list_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[FileRefEntry]: ...

    async def resolve_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        refs: list[FileRef],
    ) -> list[ResolvedInputFile]: ...
