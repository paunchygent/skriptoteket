"""Public Exam Converter contracts for the Conversion Hub lane.

Purpose:
  Define the anonymous, transient request and response models used by the
  public Exam Converter runtime without depending on FastAPI or browser state.

Relationships:
  - Used by `application.curated_apps.handlers.public_exam_converter_jobs`.
  - Serialized by `web/api/v1/public_apps_exam_converter.py`.
  - Mirrors the Sir Convert DigiExam migration bundle contract while exposing
    only Skriptoteket-owned opaque public handles to the browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import assert_never
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.application.curated_apps.sir_convert_contracts import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    DigiExamMigrationBundleSchemaVersion,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertJobStatusV2


class PublicExamConverterTarget(StrEnum):
    """Target artifacts available in the public Exam Converter lane."""

    EXAMNET_PDF = "examnet_pdf"
    QTI_PACKAGE = "qti_package"


class PublicExamConverterJobStatus(StrEnum):
    """Public-facing job lifecycle for one transient local conversion."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"

    @classmethod
    def from_sir_convert_status(
        cls,
        status: SirConvertJobStatusV2,
    ) -> "PublicExamConverterJobStatus":
        """Translate the retained Sir client status until Task 03 removes it."""

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


@dataclass(frozen=True, slots=True)
class PublicExamConverterUpload:
    """Accepted upload bytes after web-layer validation."""

    filename: str
    content_type: str
    file_bytes: bytes


@dataclass(frozen=True, slots=True)
class PublicExamConverterArtifactReadLease:
    """Retained Sir artifact lease value pending Task 03 cleanup."""

    artifact_key: str
    token: str


@dataclass(frozen=True, slots=True)
class PublicExamConverterSubmittedJob:
    """Transient local state for one anonymous in-process conversion."""

    public_job_id: str
    local_job_id: UUID
    requested_targets: tuple[PublicExamConverterTarget, ...]
    status: PublicExamConverterJobStatus
    source_filename: str
    submitted_at: datetime
    updated_at: datetime
    expires_at: datetime
    correlation_id: str | None
    error_message: str | None = None
    artifact: ExamConversionStoredArtifact | None = None
    result: dict[str, JsonValue] | None = None
    artifact_read_leases: tuple[PublicExamConverterArtifactReadLease, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicExamConverterArtifact:
    """One locally held named artifact returned through the public API."""

    filename: str
    content_type: str
    content: bytes


class PublicExamConverterSubmitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_job_id: str = Field(min_length=1)
    status: PublicExamConverterJobStatus
    requested_targets: list[PublicExamConverterTarget]
    artifact_ttl_seconds: int = Field(gt=0)
    expires_at: datetime
    poll_url: str
    result_url: str
    artifact_manifest_url: str


class PublicExamConverterJobStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_job_id: str = Field(min_length=1)
    status: PublicExamConverterJobStatus
    submitted_at: datetime
    updated_at: datetime
    expires_at: datetime
    error: str | None = None


class PublicExamConverterArtifactEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: str = Field(min_length=1)
    filename: str | None = None
    content_type: str | None = None
    availability: str
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None
    download_url: str | None = None
    unavailable_code: str | None = None


class PublicExamConverterArtifactManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: DigiExamMigrationBundleSchemaVersion = DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
    public_job_id: str = Field(min_length=1)
    status: PublicExamConverterJobStatus
    expires_at: datetime
    bundle_status: str | None = None
    artifacts: list[PublicExamConverterArtifactEntry]
    manual_follow_up: dict[str, object] | None = None
    readiness: dict[str, object] | None = None
    source_binding: dict[str, object] | None = None
    warnings: dict[str, object] | None = None


class PublicExamConverterJobResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_job_id: str = Field(min_length=1)
    status: PublicExamConverterJobStatus
    expires_at: datetime
    result: dict[str, JsonValue] | None = None
    artifact_manifest_url: str | None = None
    error: str | None = None
