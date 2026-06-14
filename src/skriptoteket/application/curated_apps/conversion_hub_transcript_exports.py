"""Conversion Hub transcript formatter export contracts.

Domain purpose:
  Define product-owned saved-transcript export requests and state snapshots
  returned to the Skriptoteket browser after backend-owned producer replay.

Relationships:
  - Returned by `web.api.v1.apps_conversion_hub_transcript_saves`.
  - Produced by `handlers.conversion_hub_transcript_formatter_exports`.
  - References persisted formatter artifacts without exposing transcript JSON,
    JobSpecs, producer receipts, or browser-carried bytes.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
)


class ConversionHubTranscriptFormatterExportStatus(StrEnum):
    """Product-owned formatter export state shown by the transcript UI."""

    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ConversionHubTranscriptFormatterExportRequest(BaseModel):
    """Record teacher intent to create formatter export artifacts."""

    model_config = ConfigDict(extra="forbid")

    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat] = Field(
        default_factory=lambda: [
            ConversionHubTranscriptFormatterArtifactFormat.TXT,
            ConversionHubTranscriptFormatterArtifactFormat.MD,
            ConversionHubTranscriptFormatterArtifactFormat.VTT,
            ConversionHubTranscriptFormatterArtifactFormat.SRT,
        ],
        min_length=1,
        max_length=4,
    )

    @field_validator("requested_artifacts")
    @classmethod
    def _requested_artifacts_are_unique(
        cls,
        value: list[ConversionHubTranscriptFormatterArtifactFormat],
    ) -> list[ConversionHubTranscriptFormatterArtifactFormat]:
        if len(set(value)) != len(value):
            raise ValueError("requested_artifacts must be unique")
        return value


class ConversionHubTranscriptFormatterExportStateRecord(BaseModel):
    """Persist product-owned formatter export intent for non-artifact states."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    transcript_id: UUID
    conversion_hub_job_id: UUID
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat] = Field(
        min_length=1,
        max_length=4,
    )
    created_at: datetime
    updated_at: datetime

    @field_validator("requested_artifacts")
    @classmethod
    def _requested_artifacts_are_unique(
        cls,
        value: list[ConversionHubTranscriptFormatterArtifactFormat],
    ) -> list[ConversionHubTranscriptFormatterArtifactFormat]:
        if len(set(value)) != len(value):
            raise ValueError("requested_artifacts must be unique")
        return value


class ConversionHubTranscriptFormatterExportArtifact(BaseModel):
    """Product-safe formatter artifact view for download and Mina filer actions."""

    model_config = ConfigDict(frozen=True)

    requested_artifact: ConversionHubTranscriptFormatterArtifactFormat
    artifact_key: ConversionHubTranscriptFormatterArtifactKey
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)


class ConversionHubTranscriptFormatterExportResponse(BaseModel):
    """Product-owned export state snapshot for one saved transcript."""

    model_config = ConfigDict(frozen=True)

    transcript_id: UUID
    conversion_hub_job_id: UUID | None
    status: ConversionHubTranscriptFormatterExportStatus
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat]
    artifacts: list[ConversionHubTranscriptFormatterExportArtifact]
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
