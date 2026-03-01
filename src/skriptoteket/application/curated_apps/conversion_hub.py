"""Conversion Hub curated app contract models (Skriptoteket).

Purpose:
  Provide a typed, stable API contract for Skriptoteket's "Conversion Hub" curated app.

Relationships:
  - Used by `src/skriptoteket/web/api/v1/apps_conversion_hub.py` as response/request models.
  - Intended to mirror the Sir Convert-a-Lot v2 job-spec surface sufficiently for a clean
    submit/poll/download orchestration flow, without embedding conversion engines in Skriptoteket.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConversionHubSourceFormatV2(StrEnum):
    """Uploaded source formats supported by Sir Convert-a-Lot v2 (mirrored)."""

    PDF = "pdf"
    MD = "md"
    HTML = "html"
    DOCX = "docx"


class ConversionHubOutputFormatV2(StrEnum):
    """Output formats supported by Sir Convert-a-Lot v2 (mirrored)."""

    MD = "md"
    PDF = "pdf"
    DOCX = "docx"


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


class ConversionHubSubmittedJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_filename: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    idempotent_replay: bool = False


class ConversionHubSubmitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[ConversionHubSubmittedJob]


class ConversionHubJobStatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
