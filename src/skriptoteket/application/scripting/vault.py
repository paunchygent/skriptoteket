from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentSummary
from skriptoteket.domain.scripting.file_refs import FileRef
from skriptoteket.domain.scripting.vault import VaultFileSourceKind, VaultListSort, VaultListState


class VaultFileInfo(BaseModel):
    """One Mina filer record; a record for a saved exam carries that exam's saved exports."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    ref: FileRef
    name: str
    bytes: int
    source_label: str | None = None
    is_missing_on_disk: bool = False
    created_at: datetime
    deleted_at: datetime | None = None
    exports: list[VaultFileInfo] = Field(default_factory=list)


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


class RenameVaultFileCommand(BaseModel):
    """Rename one owned record by its stem; the record's extension is kept (TASK-SKRIPT-37-05-04).

    A record with a document lineage renames every version of that lineage (D9).
    """

    model_config = ConfigDict(frozen=True)

    file_id: UUID
    stem: str = Field(min_length=1, max_length=255)


class RenameVaultFileResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file: VaultFileInfo
    renamed_file_ids: tuple[UUID, ...] = ()
    exam_summary: ExamWorkspaceDocumentSummary | None = None
