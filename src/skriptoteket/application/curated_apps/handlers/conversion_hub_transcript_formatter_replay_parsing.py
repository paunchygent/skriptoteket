"""Conversion Hub transcript formatter replay response parsing.

Domain purpose:
  Validate Sir Convert replay result and artifact manifest envelopes before
  Skriptoteket records downloadable transcript formatter artifact references.

Relationships:
  - Used by `conversion_hub_transcript_formatter_replay` completion handling.
  - Emits typed artifact refs from `conversion_hub_transcript_replay`.
  - Fails with domain service errors for malformed producer responses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator
from typing_extensions import Self

from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterArtifactRef,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

_ReplayFormat = ConversionHubTranscriptFormatterArtifactFormat
_ReplayArtifactKey = ConversionHubTranscriptFormatterArtifactKey

_ARTIFACT_KEY_BY_FORMAT = {
    _ReplayFormat.TXT: _ReplayArtifactKey.TRANSCRIPT_TXT,
    _ReplayFormat.MD: _ReplayArtifactKey.TRANSCRIPT_MD,
    _ReplayFormat.VTT: _ReplayArtifactKey.TRANSCRIPT_VTT,
    _ReplayFormat.SRT: _ReplayArtifactKey.TRANSCRIPT_SRT,
}
_FORMAT_BY_ARTIFACT_KEY = {value: key for key, value in _ARTIFACT_KEY_BY_FORMAT.items()}
_CONTENT_TYPE_BY_ARTIFACT_KEY = {
    _ReplayArtifactKey.TRANSCRIPT_TXT: "text/plain",
    _ReplayArtifactKey.TRANSCRIPT_MD: "text/markdown",
    _ReplayArtifactKey.TRANSCRIPT_VTT: "text/vtt",
    _ReplayArtifactKey.TRANSCRIPT_SRT: "application/x-subrip",
}


class _ReplayResultArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Literal["transcript_replay_bundle_manifest.json"]
    format: Literal["transcript_bundle"]
    content_type: Literal["application/json"]
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=1)


class _ReplayConversionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_used: Literal["transcript_json_to_transcript_bundle_replay_v2"]
    options_fingerprint: str = Field(min_length=1)
    backend_used: None = None
    acceleration_used: None = None
    acceleration_policy_requested: None = None
    chunk_size_pages: None = None
    effective_gpu_stage_limit: None = None
    formula_authority: dict[str, JsonValue] = Field(default_factory=dict)
    gpu_busy_percent: None = None
    gpu_device_count: None = None
    gpu_memory_used_percent: None = None
    gpu_runtime_kind: None = None
    max_chunk_workers: None = None
    ocr_enabled: None = None
    ocr_engine_used: None = None
    ocr_languages_used: None = None
    parallel_enabled: None = None
    scheduling_mode: None = None
    template_artifact_sha256: None = None
    template_id: None = None
    template_version: None = None

    @model_validator(mode="after")
    def _formula_authority_is_empty(self) -> Self:
        if self.formula_authority:
            raise ValueError("replay metadata must not include formula authority details")
        return self


class _ReplayResultBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact: _ReplayResultArtifact
    conversion_metadata: _ReplayConversionMetadata


class _ReplayResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: _ReplayResultBody


class _ReplayArtifactEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_key: ConversionHubTranscriptFormatterArtifactKey
    availability: Literal["available", "unavailable", "failed", "unrequested"]
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None
    retrieval_path: str | None = None
    unavailable_code: str | None = None


class _ReplayArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"]
    job_id: str = Field(min_length=1)
    output_format: Literal["transcript_bundle"]
    artifacts: list[_ReplayArtifactEntry] = Field(min_length=1)


def parse_replay_result(payload: dict[str, JsonValue]) -> None:
    try:
        _ReplayResultEnvelope.model_validate(payload)
    except ValidationError as exc:
        raise _malformed_replay_response("Sir Convert replay result is malformed.") from exc


def parse_replay_artifact_refs(
    *,
    payload: dict[str, JsonValue],
    sir_convert_job_id: str,
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
) -> list[ConversionHubTranscriptFormatterArtifactRef]:
    try:
        manifest = _ReplayArtifactManifest.model_validate(payload)
    except ValidationError as exc:
        raise _malformed_replay_response(
            "Sir Convert replay artifact manifest is malformed."
        ) from exc
    if manifest.job_id != sir_convert_job_id:
        raise _malformed_replay_response("Sir Convert replay artifact manifest has wrong job id.")

    requested_keys = {
        _ARTIFACT_KEY_BY_FORMAT[requested_artifact] for requested_artifact in requested_artifacts
    }
    accepted: dict[
        ConversionHubTranscriptFormatterArtifactKey,
        ConversionHubTranscriptFormatterArtifactRef,
    ] = {}
    seen: set[ConversionHubTranscriptFormatterArtifactKey] = set()
    for entry in manifest.artifacts:
        if entry.artifact_key in seen:
            raise _malformed_replay_response("Sir Convert replay artifact keys are duplicated.")
        seen.add(entry.artifact_key)
        if entry.unavailable_code == "not_implemented":
            raise _malformed_replay_response("Sir Convert replay artifact is not implemented.")
        if entry.artifact_key not in requested_keys:
            continue
        accepted[entry.artifact_key] = _available_artifact_ref(entry)

    missing = [artifact_key for artifact_key in requested_keys if artifact_key not in accepted]
    if missing:
        raise _malformed_replay_response("Sir Convert replay artifact manifest is incomplete.")
    return [accepted[_ARTIFACT_KEY_BY_FORMAT[artifact]] for artifact in requested_artifacts]


def _available_artifact_ref(
    entry: _ReplayArtifactEntry,
) -> ConversionHubTranscriptFormatterArtifactRef:
    expected_content_type = _CONTENT_TYPE_BY_ARTIFACT_KEY[entry.artifact_key]
    if entry.availability != "available":
        raise _malformed_replay_response("Requested Sir Convert replay artifact is unavailable.")
    if entry.content_type != expected_content_type:
        raise _malformed_replay_response("Sir Convert replay artifact content type is invalid.")
    if (
        entry.filename is None
        or entry.size_bytes is None
        or entry.sha256 is None
        or entry.retrieval_path is None
    ):
        raise _malformed_replay_response("Sir Convert replay artifact ref is incomplete.")
    return ConversionHubTranscriptFormatterArtifactRef(
        requested_artifact=_FORMAT_BY_ARTIFACT_KEY[entry.artifact_key],
        artifact_key=entry.artifact_key,
        filename=entry.filename,
        content_type=entry.content_type,
        size_bytes=entry.size_bytes,
        sha256=entry.sha256,
        retrieval_path=entry.retrieval_path,
    )


def _malformed_replay_response(message: str) -> DomainError:
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=message,
        details={"upstream": "sir_convert_transcript_formatter_replay"},
    )
