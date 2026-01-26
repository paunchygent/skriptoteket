from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VaultFileSourceKind(StrEnum):
    RUN_ARTIFACT = "run_artifact"


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
    created_at: datetime
    deleted_at: datetime | None = None


class VaultUsage(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    user_id: UUID
    bytes_total: int
    updated_at: datetime
