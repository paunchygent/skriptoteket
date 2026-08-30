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
from typing import assert_never
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertJobStatusV2


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


def build_conversion_hub_v2_job_spec(
    *,
    spec: ConversionHubJobSpecV2,
    filename: str,
) -> dict[str, object]:
    """Build the Sir Convert-a-Lot v2 job spec payload for one upload."""
    if spec.output_format.value != "pdf" and spec.pdf_layout is not None:
        raise validation_error("pdf_layout is only supported for PDF outputs.")
    job_spec: dict[str, object] = {
        "api_version": "v2",
        "source": {
            "kind": "upload",
            "filename": filename,
            "format": spec.source_format.value,
        },
        "conversion": {
            "output_format": spec.output_format.value,
            "css_filenames": [],
            "pdf_layout": spec.pdf_layout.model_dump(mode="json")
            if spec.pdf_layout is not None
            else None,
            "template": None,
            "reference_docx_filename": None,
        },
        "pdf_options": None,
        "execution": None,
        "retention": {"pin": False},
    }
    if spec.source_format.value == "pdf":
        # Safe defaults required by Sir Convert-a-Lot v2 for PDF sources.
        job_spec["pdf_options"] = {
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": "accurate",
            "normalize": "standard",
        }
        job_spec["execution"] = {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 1800,
        }
    return job_spec


class ConversionHubJobStatus(StrEnum):
    """Normalize the locally owned Conversion Hub job lifecycle."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

    @classmethod
    def from_sir_convert_status(
        cls,
        status: SirConvertJobStatusV2,
    ) -> "ConversionHubJobStatus":
        """Translate typed Sir Convert v2 job state into the local product lifecycle."""

        match status:
            case SirConvertJobStatusV2.QUEUED:
                return cls.QUEUED
            case SirConvertJobStatusV2.RUNNING:
                return cls.PROCESSING
            case SirConvertJobStatusV2.SUCCEEDED:
                return cls.SUCCEEDED
            case SirConvertJobStatusV2.FAILED:
                return cls.FAILED
            case SirConvertJobStatusV2.CANCELED:
                return cls.CANCELED
        assert_never(status)


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
    submission_idempotency_key: str | None = None
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
