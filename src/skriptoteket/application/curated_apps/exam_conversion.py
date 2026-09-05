"""Exam Converter in-process conversion contracts.

Purpose:
    Define the product-facing models and local-producer identity helpers for
    the in-process dxe -> Exam.net bundle lane owned by the Conversion Hub
    curated app.

Relationships:
    Used by ``application.curated_apps.handlers.exam_converter_conversions``,
    ``application.curated_apps.exam_conversion_producers``, and the Conversion
    Hub artifact download handler for local-lane branching.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename

EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME = "qti-package.zip"
EXAMNET_BUNDLE_PDF_FILENAME = "examnet-import.pdf"
EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME = "qti-validation-report.json"
_MAX_FILENAME_LENGTH = 255
_MAX_EXAMNET_BUNDLE_FILENAME_LENGTH = 270
_EXAMNET_PDF_FILENAME_SUFFIX = " - Exam.net.pdf"
_EXAMNET_QTI_FILENAME_SUFFIX = " - QTI.zip"


class ExamConversionStoredArtifact(BaseModel):
    """Represent one server-owned in-process Exam Converter result bundle."""

    model_config = ConfigDict(frozen=True)

    filename: str = Field(min_length=1, max_length=_MAX_EXAMNET_BUNDLE_FILENAME_LENGTH)
    content_type: str = Field(min_length=1, max_length=255)
    content: bytes = Field(min_length=1)
    source_filename: str = Field(min_length=1, max_length=255)
    source_content: bytes = Field(min_length=1)
    named_artifacts: tuple["ExamConversionNamedArtifact", ...] = ()


class ExamConversionNamedArtifact(BaseModel):
    """One product-facing artifact owned by a local Exam Converter job."""

    model_config = ConfigDict(frozen=True)

    artifact_key: str = Field(min_length=1, max_length=128)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    content: bytes = Field(min_length=1)


class ExamConverterConversionSubmitResult(BaseModel):
    """Return the locally owned job created for one in-process conversion."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: ConversionHubJobStatus
    error: str | None = None
    idempotent_replay: bool = False


def is_exam_conversion_job(job: ConversionHubJob) -> bool:
    """Return true for the Skriptoteket-owned Exam Converter job shape."""
    return job.source_format.value == "dxe" and job.output_format.value == "examnet_bundle"


def build_examnet_bundle_filename(*, input_filename: str) -> str:
    """Build the downloadable bundle filename for one converted `.dxe` upload."""
    stem = input_filename.rsplit(".", 1)[0] if "." in input_filename else input_filename
    return f"{stem}-examnet-bundle.zip"


def build_examnet_pdf_filename(*, input_filename: str) -> str:
    """Build a source-identifying filename for the Exam.net PDF target."""
    return _build_examnet_target_filename(
        input_filename=input_filename,
        suffix=_EXAMNET_PDF_FILENAME_SUFFIX,
    )


def build_examnet_qti_filename(*, input_filename: str) -> str:
    """Build a source-identifying filename for the QTI package target."""
    return _build_examnet_target_filename(
        input_filename=input_filename,
        suffix=_EXAMNET_QTI_FILENAME_SUFFIX,
    )


def _build_examnet_target_filename(*, input_filename: str, suffix: str) -> str:
    safe_filename = sanitize_input_filename(input_filename=input_filename)
    source_stem = safe_filename[:-4] if safe_filename.casefold().endswith(".dxe") else safe_filename
    if not source_stem:
        raise validation_error("DigiExam source filename must include a stem.")
    available_stem_length = _MAX_FILENAME_LENGTH - len(suffix)
    bounded_stem = source_stem[:available_stem_length]
    return sanitize_input_filename(input_filename=f"{bounded_stem}{suffix}")
