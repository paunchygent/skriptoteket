"""Conversion Hub saved artifact contracts.

Purpose:
  Describe owner-scoped user-file persistence for authenticated Exam Converter
  artifacts produced by Sir Convert while keeping Vault persistence independent
  from browser transport and upstream token authority.

Relationships:
  - Used by `web.api.v1.apps_conversion_hub` for the authenticated save route.
  - Consumed by `handlers.conversion_hub_artifact_saves` to validate metadata
    and persist `APP_EXPORT` Vault files.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.sir_convert_contracts import (
    DigiExamMigrationBundleSchemaVersion,
)


class ConversionHubSirConvertArtifactSaveMetadata(BaseModel):
    """Metadata retained when a Sir Convert named artifact is saved to user files."""

    model_config = ConfigDict(extra="forbid")

    sir_convert_job_id: str = Field(min_length=1, max_length=255)
    artifact_key: str = Field(min_length=1, max_length=128)
    source_filename: str = Field(min_length=1, max_length=255)
    saved_display_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    bundle_schema_version: DigiExamMigrationBundleSchemaVersion
    correlation_id: str = Field(min_length=1, max_length=128)
    saved_at: datetime


class SaveConversionHubSirConvertArtifactCommand(BaseModel):
    """Application command for saving one downloaded Sir Convert artifact."""

    model_config = ConfigDict(frozen=True)

    metadata: ConversionHubSirConvertArtifactSaveMetadata
    filename: str
    content_type: str
    content: bytes


class ConversionHubSavedVaultArtifact(BaseModel):
    """Teacher-facing summary of the saved user-file artifact."""

    model_config = ConfigDict(frozen=True)

    file_id: UUID
    name: str
    bytes: int
    created_at: datetime


class SaveConversionHubSirConvertArtifactResult(BaseModel):
    """Result returned after one Sir Convert artifact has been saved."""

    model_config = ConfigDict(frozen=True)

    vault_artifact: ConversionHubSavedVaultArtifact
    source_artifact_id: str
