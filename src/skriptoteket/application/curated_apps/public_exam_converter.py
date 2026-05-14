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

from pydantic import BaseModel, ConfigDict, Field


class PublicExamConverterTarget(StrEnum):
    """Target artifacts available in the public Exam Converter lane."""

    EXAMNET_PDF = "examnet_pdf"
    QTI_PACKAGE = "qti_package"


class PublicExamConverterJobStatus(StrEnum):
    """Public-facing job lifecycle normalized from Sir Convert status values."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"

    @classmethod
    def from_upstream(cls, status: str) -> "PublicExamConverterJobStatus":
        normalized = status.strip().lower()
        if normalized in {"running", "processing"}:
            return cls.PROCESSING
        if normalized == "cancelled":
            return cls.CANCELED
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class PublicExamConverterUpload:
    """Accepted upload bytes after web-layer validation."""

    filename: str
    content_type: str
    file_bytes: bytes


@dataclass(frozen=True, slots=True)
class PublicExamConverterArtifactReadLease:
    """Server-side Sir Convert read lease for one named public artifact."""

    artifact_key: str
    token: str


@dataclass(frozen=True, slots=True)
class PublicExamConverterSubmittedJob:
    """Transient local state created for one public upstream job."""

    public_job_id: str
    upstream_job_id: str
    grant_token: str
    manifest_artifact_read_lease_token: str
    requested_targets: tuple[PublicExamConverterTarget, ...]
    status: PublicExamConverterJobStatus
    source_filename: str
    submitted_at: datetime
    updated_at: datetime
    expires_at: datetime
    correlation_id: str | None
    error_message: str | None = None
    artifact_read_leases: tuple[PublicExamConverterArtifactReadLease, ...] = ()


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
    blocker_code: str | None = None


class PublicExamConverterArtifactManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "digiexam_migration_bundle_v1"
    public_job_id: str = Field(min_length=1)
    status: PublicExamConverterJobStatus
    expires_at: datetime
    bundle_status: str | None = None
    artifacts: list[PublicExamConverterArtifactEntry]
    manual_follow_up: dict[str, object] | None = None
    warnings: dict[str, object] | None = None


class PublicExamConverterJobResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_job_id: str = Field(min_length=1)
    status: PublicExamConverterJobStatus
    expires_at: datetime
    result: dict[str, object] | None = None
    artifact_manifest_url: str | None = None
    error: str | None = None
