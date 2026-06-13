"""Conversion Hub curated app models and local job contracts.

Purpose:
  Define the stable product-facing request/response models for the Conversion Hub
  curated app plus the local job-ledger state tracked by Skriptoteket.

Relationships:
  - Used by `src/skriptoteket/web/api/v1/apps_conversion_hub.py` for request/response
    serialization.
  - Used by `application.curated_apps.handlers.conversion_hub_jobs` to normalize
    upstream Sir Convert state into locally owned Conversion Hub jobs.
  - Persisted via `protocols.conversion_hub.ConversionHubJobRepositoryProtocol`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.errors import DomainError, ErrorCode


class ConversionHubSourceFormatV2(StrEnum):
    """Uploaded source formats supported by Sir Convert-a-Lot v2 (mirrored)."""

    AUDIO = "audio"
    TRANSCRIPT_JSON = "transcript_json"
    PDF = "pdf"
    MD = "md"
    HTML = "html"
    DOCX = "docx"
    DIGIEXAM_DXE = "dxe"


class ConversionHubOutputFormatV2(StrEnum):
    """Output formats supported by Sir Convert-a-Lot v2 (mirrored)."""

    MD = "md"
    PDF = "pdf"
    DOCX = "docx"
    EXAMNET_BUNDLE = "examnet_bundle"
    TRANSCRIPT_BUNDLE = "transcript_bundle"


class ConversionHubPdfPaperSizeV2(StrEnum):
    """Supported PDF paper sizes for v2 PDF outputs (mirrored)."""

    A5 = "a5"
    A4 = "a4"
    A3 = "a3"


class ConversionHubPdfOrientationV2(StrEnum):
    """Supported PDF orientations for v2 PDF outputs (mirrored)."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class ConversionHubPdfLayoutV2(BaseModel):
    """Typed PDF layout presets (mirrors Sir Convert-a-Lot v2 `conversion.pdf_layout`)."""

    model_config = ConfigDict(extra="forbid")

    paper_size: ConversionHubPdfPaperSizeV2 = ConversionHubPdfPaperSizeV2.A4
    orientation: ConversionHubPdfOrientationV2 = ConversionHubPdfOrientationV2.PORTRAIT
    margins_mm: int = Field(default=12, ge=0, le=50)


class ConversionHubRouteV2(BaseModel):
    """One supported conversion route."""

    model_config = ConfigDict(extra="forbid")

    source_format: ConversionHubSourceFormatV2
    output_format: ConversionHubOutputFormatV2
    title: str = Field(min_length=1)


class ConversionHubListRoutesResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routes: list[ConversionHubRouteV2]


class ConversionHubJobSpecV2(BaseModel):
    """Conversion Hub job spec (a constrained mirror of Sir Convert-a-Lot v2 JobSpecV2).

    This is the payload the SPA submits as JSON (embedded in multipart for file uploads).
    The backend turns it into a v2 JobSpec dict to submit to Sir Convert-a-Lot.
    """

    model_config = ConfigDict(extra="forbid")

    source_format: ConversionHubSourceFormatV2
    output_format: ConversionHubOutputFormatV2
    pdf_layout: ConversionHubPdfLayoutV2 | None = None


class ConversionHubJobStatus(StrEnum):
    """Normalize the locally owned Conversion Hub job lifecycle."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

    @classmethod
    def from_upstream(cls, status: str) -> "ConversionHubJobStatus":
        """Map Sir Convert status strings onto the local Conversion Hub contract."""
        normalized = status.strip().lower()
        if normalized == "cancelled":
            normalized = "canceled"
        try:
            return cls(normalized)
        except ValueError as exc:
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Unsupported Conversion Hub upstream status: {status}",
                details={"status": status},
            ) from exc


class ConversionHubJob(BaseModel):
    """Persist one locally owned Conversion Hub conversion job."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    input_filename: str = Field(min_length=1)
    source_format: ConversionHubSourceFormatV2
    output_format: ConversionHubOutputFormatV2
    pdf_layout: ConversionHubPdfLayoutV2 | None = None
    upstream_job_id: str | None = None
    status: ConversionHubJobStatus
    correlation_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversionHubSubmittedJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_filename: str = Field(min_length=1)
    job_id: UUID
    status: ConversionHubJobStatus
    error: str | None = None


class ConversionHubSubmitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[ConversionHubSubmittedJob]


class ConversionHubJobStatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: ConversionHubJobStatus
    error: str | None = None


class RegisterExamConverterConversionHubJobRequest(BaseModel):
    """Register one upstream Exam Converter job in Skriptoteket's local ledger."""

    model_config = ConfigDict(extra="forbid")

    upstream_job_id: str = Field(min_length=1, max_length=255)
    input_filename: str = Field(min_length=1, max_length=255)
    correlation_id: str | None = Field(default=None, max_length=64)
    status: ConversionHubJobStatus = ConversionHubJobStatus.SUCCEEDED


class RegisterExamConverterConversionHubJobResult(BaseModel):
    """Return the owner-scoped local Conversion Hub job id for corrections."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    upstream_job_id: str
    status: ConversionHubJobStatus


class RegisterTranscriptConversionHubJobRequest(BaseModel):
    """Register one upstream transcript job in Skriptoteket's local ledger."""

    model_config = ConfigDict(extra="forbid")

    upstream_job_id: str = Field(min_length=1, max_length=255)
    input_filename: str = Field(min_length=1, max_length=255)
    correlation_id: str | None = Field(default=None, max_length=128)
    status: ConversionHubJobStatus = ConversionHubJobStatus.SUCCEEDED


class RegisterTranscriptConversionHubJobResult(BaseModel):
    """Return the owner-scoped local Conversion Hub transcript job id."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    upstream_job_id: str
    status: ConversionHubJobStatus
