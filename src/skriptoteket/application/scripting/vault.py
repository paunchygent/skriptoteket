from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.scripting.file_refs import FileRef
from skriptoteket.domain.scripting.vault import VaultFileSourceKind, VaultListSort, VaultListState


class VaultFileInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    ref: FileRef
    name: str
    bytes: int
    created_at: datetime
    deleted_at: datetime | None = None


class VaultUsageInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    bytes_total: int
    max_total_bytes: int
    max_file_bytes: int


class ListVaultFilesQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: VaultListState = VaultListState.ACTIVE
    search: str | None = None
    sort: VaultListSort = VaultListSort.NEWEST
    limit: int = 50
    cursor: int | None = None


class ListVaultFilesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: VaultListState
    search: str | None
    sort: VaultListSort
    files: list[VaultFileInfo] = Field(default_factory=list)
    usage: VaultUsageInfo
    next_cursor: str | None = None


class SaveVaultFileCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_kind: VaultFileSourceKind
    run_id: UUID
    artifact_id: str
    name: str | None = None


class SaveVaultFileResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: VaultFileInfo


class DeleteVaultFileCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: UUID


class DeleteVaultFileResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: VaultFileInfo


class RestoreVaultFileCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: UUID


class RestoreVaultFileResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: VaultFileInfo
