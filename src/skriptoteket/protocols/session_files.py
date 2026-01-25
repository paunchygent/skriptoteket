from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionFileContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    content: bytes
    field: str


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
    field: str | None = None


class SessionFileStorageProtocol(Protocol):
    async def store_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        files: list[SessionFileContent],
    ) -> None: ...

    async def get_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[SessionFileContent]: ...

    async def get_files_by_name(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        names: list[str],
    ) -> list[SessionFileContent]: ...

    async def upsert_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        files: list[SessionFileContent],
    ) -> None: ...

    async def list_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[SessionFileMetadata]: ...

    async def delete_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        names: list[str],
    ) -> int: ...

    async def clear_session(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> None: ...

    async def clear_all(self) -> None: ...

    async def cleanup_expired(self) -> CleanupExpiredSessionFilesResult: ...
