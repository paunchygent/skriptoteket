from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.models import RunStatus


class RunnerArtifact(BaseModel):
    """Artifact metadata reported by the runner via result.json (ADR-0015)."""

    model_config = ConfigDict(frozen=True)

    path: str
    bytes: int


class StoredArtifact(BaseModel):
    """Artifact metadata after app-side validation + persistence to disk."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    path: str
    bytes: int


class ArtifactsManifest(BaseModel):
    """Manifest stored in DB; binaries live on disk (ADR-0012)."""

    model_config = ConfigDict(frozen=True)

    artifacts: list[StoredArtifact]


class ToolExecutionResult(BaseModel):
    """Final execution result produced by ToolRunnerProtocol (not a DB model)."""

    model_config = ConfigDict(frozen=True)

    status: RunStatus
    stdout: str
    stderr: str
    html_output: str
    error_summary: str | None
    artifacts_manifest: ArtifactsManifest
