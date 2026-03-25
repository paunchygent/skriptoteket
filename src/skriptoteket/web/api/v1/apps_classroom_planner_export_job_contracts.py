"""Web DTOs for classroom-planner seating export jobs.

Purpose:
    Define the public request and response envelopes for the PR-0119 async
    seating export-job lane without exposing raw Sir Convert or Vault internals.

Relationships:
    - Serializes application export-job models from
      `application.curated_apps.classroom_planner.exports`.
    - Used by the seating-specific classroom-planner API router.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJobResult,
    SeatingExportJobStatus,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)


class CreateSeatingExportJobRequest(BaseModel):
    """Deserialize the public job-creation payload for seating exports."""

    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId | None = None
    paper_size: SeatingExportPaperSize | None = None

    @model_validator(mode="after")
    def validate_export_shape(self) -> CreateSeatingExportJobRequest:
        """Require PDF layout inputs only for PDF exports."""

        if self.export_kind is SeatingExportKind.PDF:
            if self.layout_id is None or self.paper_size is None:
                raise ValueError("PDF-export kräver layout och pappersstorlek.")
            return self
        if self.layout_id is not None or self.paper_size is not None:
            raise ValueError("Excel-export använder inte layout eller pappersstorlek.")
        return self


class SeatingExportVaultArtifactDto(BaseModel):
    """Serialize the teacher-facing summary for a saved Vault export artifact."""

    model_config = ConfigDict(frozen=True)

    file_id: UUID
    name: str
    bytes: int
    created_at: datetime


class SeatingExportJobDto(BaseModel):
    """Serialize one classroom-planner seating export job."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    draft_id: UUID
    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId | None = None
    paper_size: SeatingExportPaperSize | None = None
    status: SeatingExportJobStatus
    created_at: datetime
    download_url: str | None = None
    vault_artifact: SeatingExportVaultArtifactDto | None = None
    error: str | None = None


def serialize_seating_export_job(job: SeatingExportJobResult) -> SeatingExportJobDto:
    """Map one application export-job result to the public API DTO."""

    vault_artifact = None
    if job.vault_artifact is not None:
        vault_artifact = SeatingExportVaultArtifactDto(
            file_id=job.vault_artifact.file_id,
            name=job.vault_artifact.name,
            bytes=job.vault_artifact.bytes,
            created_at=job.vault_artifact.created_at,
        )
    return SeatingExportJobDto(
        job_id=job.job_id,
        draft_id=job.draft_id,
        export_kind=job.export_kind,
        layout_id=job.layout_id,
        paper_size=job.paper_size,
        status=job.status,
        created_at=job.created_at,
        download_url=job.download_url,
        vault_artifact=vault_artifact,
        error=job.error,
    )
