"""Application models for classroom-planner export-job orchestration.

Purpose:
    Define typed job-state contracts for explicit seating exports so the
    application layer can orchestrate async HTML/CSS rendering, conversion, and
    Vault delivery without leaking persistence or web concerns.

Relationships:
    - Persisted through `SeatingExportJobRepositoryProtocol`.
    - Returned by seating export-job handlers for web serialization.
    - References the PR-0118 prepare-contract enums from `models.py`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .models import SeatingExportKind, SeatingExportLayoutId


class SeatingExportPaperSize(StrEnum):
    """Enumerate the teacher-selectable paper sizes for poster export."""

    A3_LANDSCAPE = "a3_landscape"
    A4_LANDSCAPE = "a4_landscape"


class SeatingExportJobStatus(StrEnum):
    """Enumerate async export lifecycle states surfaced by the API."""

    SUBMITTED = "submitted"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SeatingExportVaultArtifact(BaseModel):
    """Describe the durable Vault artifact produced by a completed export job."""

    model_config = ConfigDict(frozen=True)

    file_id: UUID
    name: str
    bytes: int
    created_at: datetime


class SeatingExportJob(BaseModel):
    """Describe one explicit seating export job tracked by the backend."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    draft_id: UUID
    roster_id: UUID
    template_id: UUID
    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId
    paper_size: SeatingExportPaperSize
    output_filename: str
    status: SeatingExportJobStatus
    upstream_job_id: str | None = None
    webhook_subscription_id: str | None = None
    webhook_secret: str | None = None
    vault_file_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SeatingExportJobResult(BaseModel):
    """Describe the teacher-facing export-job payload returned by handlers."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    draft_id: UUID
    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId
    paper_size: SeatingExportPaperSize
    status: SeatingExportJobStatus
    created_at: datetime
    download_url: str | None = None
    vault_artifact: SeatingExportVaultArtifact | None = None
    error: str | None = None
