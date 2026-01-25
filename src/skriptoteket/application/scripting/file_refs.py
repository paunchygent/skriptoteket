from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FileRefInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: str
    name: str
    bytes: int
    field: str | None = None


class ListToolFileRefsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str


class ListToolFileRefsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    files: list[FileRefInfo] = Field(default_factory=list)


class ListSandboxFileRefsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    snapshot_id: UUID


class ListSandboxFileRefsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    snapshot_id: UUID
    files: list[FileRefInfo] = Field(default_factory=list)
