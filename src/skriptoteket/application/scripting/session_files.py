from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionFileInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    bytes: int
    ref: str
    field: str | None = None


class ListSessionFilesQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str


class ListSessionFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    files: list[SessionFileInfo] = Field(default_factory=list)


class DeleteSessionFilesCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    names: list[str] = Field(default_factory=list)


class DeleteSessionFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    deleted: int


class ListSandboxSessionFilesQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    snapshot_id: UUID


class ListSandboxSessionFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    snapshot_id: UUID
    files: list[SessionFileInfo] = Field(default_factory=list)


class DeleteSandboxSessionFilesCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    snapshot_id: UUID
    names: list[str] = Field(default_factory=list)


class DeleteSandboxSessionFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    snapshot_id: UUID
    deleted: int
