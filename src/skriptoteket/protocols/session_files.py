from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

type InputFile = tuple[str, bytes]


class CleanupExpiredSessionFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scanned_sessions: int
    deleted_sessions: int
    deleted_files: int
    deleted_bytes: int


class SessionFileMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    bytes: int


class SessionFileStorageProtocol(Protocol):
    async def store_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        files: list[InputFile],
    ) -> None: ...

    async def get_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[InputFile]: ...

    async def list_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[SessionFileMetadata]: ...

    async def clear_session(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> None: ...

    async def clear_all(self) -> None: ...

    async def cleanup_expired(self) -> CleanupExpiredSessionFilesResult: ...
