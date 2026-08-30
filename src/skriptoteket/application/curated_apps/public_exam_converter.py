"""Public Exam Converter contracts for the Conversion Hub lane.

Purpose:
  Define the anonymous, transient request and response models used by the
  public Exam Converter runtime without depending on FastAPI or browser state.

Relationships:
  - Used by `application.curated_apps.handlers.public_exam_converter_jobs`.
  - Serialized by `web/api/v1/public_apps_exam_converter.py`.
  - Exposes Skriptoteket-owned opaque public handles to the browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_schema_versions import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    DigiExamMigrationBundleSchemaVersion,
)


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


@dataclass(frozen=True, slots=True)
class PublicExamConverterUpload:
    """Accepted upload bytes after web-layer validation."""

    filename: str
    content_type: str
    file_bytes: bytes


@dataclass(frozen=True, slots=True)
class PublicExamConverterSubmittedJob:
    """PostgreSQL-backed state and input for one anonymous conversion."""

    public_job_id: str
    local_job_id: UUID
    requested_targets: tuple[PublicExamConverterTarget, ...]
    status: PublicExamConverterJobStatus
    source_filename: str
    submitted_at: datetime
    updated_at: datetime
    expires_at: datetime
    correlation_id: str | None
    source_dxe: PublicExamConverterUpload
    graded_result_pdf: PublicExamConverterUpload | None = None
    locked_by: str | None = None
    locked_until: datetime | None = None
    error_message: str | None = None
    result: dict[str, JsonValue] | None = None


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
