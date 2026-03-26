"""Application models for classroom-planner grouping export jobs.

Purpose:
    Define typed job-state contracts for explicit grouping exports so the
    application layer can evolve the grouping XLSX and PDF lanes without
    leaking persistence or web concerns.

Relationships:
    - Persisted through `GroupingExportJobRepositoryProtocol`.
    - Returned by grouping export-job handlers for web serialization.
    - References the grouping presentation enums from `grouping_presentation.py`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .grouping_presentation import GroupingExportKind, GroupingExportPaperSize


class GroupingExportJobStatus(StrEnum):
    """Enumerate async grouping export lifecycle states surfaced by the API."""

    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GroupingExportVaultArtifact(BaseModel):
    """Describe the durable Vault artifact produced by a completed grouping export job."""

    model_config = ConfigDict(frozen=True)

    file_id: UUID
    name: str
    bytes: int
    created_at: datetime


class GroupingExportJob(BaseModel):
    """Describe one explicit grouping export job tracked by the backend."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    draft_id: UUID
    roster_id: UUID
    export_kind: GroupingExportKind
    paper_size: GroupingExportPaperSize | None = None
    output_filename: str
    status: GroupingExportJobStatus
    upstream_job_id: str | None = None
    webhook_subscription_id: str | None = None
    webhook_secret: str | None = None
    vault_file_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class GroupingExportJobResult(BaseModel):
    """Describe the teacher-facing grouping export-job payload returned by handlers."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    draft_id: UUID
    export_kind: GroupingExportKind
    paper_size: GroupingExportPaperSize | None = None
    status: GroupingExportJobStatus
    created_at: datetime
    download_url: str | None = None
    vault_artifact: GroupingExportVaultArtifact | None = None
    error: str | None = None
