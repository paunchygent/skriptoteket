from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class RunnerArtifact(BaseModel):
    """Artifact metadata reported by the runner via result.json (ADR-0022)."""

    model_config = ConfigDict(frozen=True)

    path: str
    bytes: int

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("path is required")
        return normalized

    @field_validator("bytes")
    @classmethod
    def _validate_bytes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("bytes must be >= 0")
        return value


class StoredArtifact(BaseModel):
    """Artifact metadata after app-side validation + persistence to disk."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    path: str
    bytes: int

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("artifact_id is required")
        return normalized

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("path is required")
        return normalized

    @field_validator("bytes")
    @classmethod
    def _validate_bytes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("bytes must be >= 0")
        return value


class ArtifactsManifest(BaseModel):
    """Manifest stored in DB; binaries live on disk (ADR-0012)."""

    model_config = ConfigDict(frozen=True)

    artifacts: list[StoredArtifact]
