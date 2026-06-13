"""Conversion Hub transcript formatter artifact action contracts.

Domain purpose:
  Define owner-scoped replay artifact provenance and action results for
  downloading or saving overlay-aware transcript formatter outputs.

Relationships:
  - Persisted by `infrastructure.repositories.conversion_hub_transcript_formatter_artifacts`.
  - Consumed by `handlers.conversion_hub_transcript_artifact_actions`.
  - Serialized by `web.api.v1.apps_conversion_hub_transcript_saves`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
)


class ConversionHubTranscriptFormatterArtifactRecord(BaseModel):
    """Persisted producer replay artifact reference for one saved transcript."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    transcript_id: UUID
    conversion_hub_job_id: UUID
    sir_convert_job_id: str = Field(min_length=1, max_length=255)
    requested_artifact: ConversionHubTranscriptFormatterArtifactFormat
    artifact_key: ConversionHubTranscriptFormatterArtifactKey
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=1, max_length=128)
    retrieval_path: str = Field(min_length=1, max_length=500)
    content: bytes | None = None
    created_at: datetime
    updated_at: datetime


class ConversionHubTranscriptFormatterArtifactDownload(BaseModel):
    """Downloaded producer artifact bytes prepared for an HTTP response."""

    model_config = ConfigDict(frozen=True)

    filename: str
    content_type: str
    content: bytes


class SaveConversionHubTranscriptFormatterArtifactResult(BaseModel):
    """Result returned after saving one transcript formatter artifact."""

    model_config = ConfigDict(frozen=True)

    vault_artifact: ConversionHubSavedVaultArtifact
    source_artifact_id: str
