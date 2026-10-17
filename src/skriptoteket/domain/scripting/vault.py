from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VaultFileSourceKind(StrEnum):
    RUN_ARTIFACT = "run_artifact"
    APP_EXPORT = "app_export"


class VaultListState(StrEnum):
    ACTIVE = "active"
    TRASH = "trash"


class VaultListSort(StrEnum):
    NEWEST = "newest"
    NAME = "name"
    SIZE = "size"


class VaultFile(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    bytes: int
    source_kind: VaultFileSourceKind
    source_run_id: UUID | None = None
    source_artifact_id: str | None = None
    document_lineage_id: UUID | None = None
    document_version: int | None = None
    export_format: str | None = None
    document_saved_at: datetime | None = None
    created_at: datetime
    deleted_at: datetime | None = None
    # Internal lifecycle state, never serialized: while the row sits in the trash, the
    # flag says whether the exam put it there, so restoring the exam returns the saved
    # exports that went with it and not one the user trashed on its own.
    trashed_with_exam: bool = Field(default=False, exclude=True)


class VaultUsage(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    user_id: UUID
    bytes_total: int
    updated_at: datetime
