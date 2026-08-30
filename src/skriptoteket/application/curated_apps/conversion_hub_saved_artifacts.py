"""Conversion Hub saved artifact result contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversionHubSavedVaultArtifact(BaseModel):
    """Teacher-facing summary of the saved user-file artifact."""

    model_config = ConfigDict(frozen=True)

    file_id: UUID
    name: str
    bytes: int
    created_at: datetime


class SaveConversionHubArtifactResult(BaseModel):
    """Result returned after one Conversion Hub artifact has been saved."""

    model_config = ConfigDict(frozen=True)

    vault_artifact: ConversionHubSavedVaultArtifact
    source_artifact_id: str
