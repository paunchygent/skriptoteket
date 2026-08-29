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

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
)

LOCAL_EXAM_CONVERSION_PRODUCER_PREFIX = "local-exam:"

EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME = "qti-package.zip"
EXAMNET_BUNDLE_PDF_FILENAME = "examnet-import.pdf"
EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME = "qti-validation-report.json"

ExamConverterConversionLaneValue = Literal["sir_convert", "in_process"]


@dataclass(frozen=True)
class ExamConverterConversionLane:
    """Operator-configured conversion lane for the authenticated Exam Converter."""

    value: ExamConverterConversionLaneValue


class ExamConversionStoredArtifact(BaseModel):
    """Represent one server-owned in-process Exam Converter result bundle."""

    model_config = ConfigDict(frozen=True)

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    content: bytes = Field(min_length=1)


class ExamConverterConversionSubmitResult(BaseModel):
    """Return the locally owned job created for one in-process conversion."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: ConversionHubJobStatus
    error: str | None = None


def is_local_exam_conversion_job(job: ConversionHubJob) -> bool:
    """Return true when an Exam Converter job was produced in-process."""
    upstream_id = job.upstream_job_id or ""
    return upstream_id.startswith(LOCAL_EXAM_CONVERSION_PRODUCER_PREFIX)


def build_local_exam_conversion_producer_id(*, job_id: UUID) -> str:
    """Build the local producer identity stored on the existing job ledger."""
    return f"{LOCAL_EXAM_CONVERSION_PRODUCER_PREFIX}{job_id}"


def build_examnet_bundle_filename(*, input_filename: str) -> str:
    """Build the downloadable bundle filename for one converted `.dxe` upload."""
    stem = input_filename.rsplit(".", 1)[0] if "." in input_filename else input_filename
    return f"{stem}-examnet-bundle.zip"
