"""Conversion Hub transcript formatter replay contracts.

Domain purpose:
  Define typed request, JobSpec, and artifact-reference envelopes for replaying
  producer-owned transcript formatter artifacts from saved canonical JSON plus
  Skriptoteket speaker overlays.

Relationships:
  - Built by `handlers.conversion_hub_transcript_formatter_replay`.
  - Serialized by `web.api.v1.apps_conversion_hub_transcript_saves`.
  - Submitted through the browser-session HuleEdu Sir Convert Gateway client.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubTranscriptSpeakerOverlayEntry,
)


class ConversionHubTranscriptFormatterArtifactFormat(StrEnum):
    """Closed artifact format values accepted by Sir Convert replay."""

    TXT = "txt"
    MD = "md"
    VTT = "vtt"
    SRT = "srt"


class ConversionHubTranscriptFormatterArtifactKey(StrEnum):
    """Closed named replay artifact keys returned by Sir Convert."""

    TRANSCRIPT_TXT = "transcript_txt"
    TRANSCRIPT_MD = "transcript_md"
    TRANSCRIPT_VTT = "transcript_vtt"
    TRANSCRIPT_SRT = "transcript_srt"


class ConversionHubTranscriptFormatterReplaySource(BaseModel):
    """Replay source descriptor for one uploaded canonical transcript JSON file."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["upload"] = "upload"
    filename: str = Field(min_length=1, max_length=255)
    format: Literal["transcript_json"] = "transcript_json"


class ConversionHubTranscriptFormatterReplayConversion(BaseModel):
    """Replay conversion target descriptor."""

    model_config = ConfigDict(extra="forbid")

    output_format: Literal["transcript_bundle"] = "transcript_bundle"


class ConversionHubTranscriptFormatterReplayRetention(BaseModel):
    """Replay retention descriptor; pinning remains producer-rejected."""

    model_config = ConfigDict(extra="forbid")

    pin: Literal[False] = False


class ConversionHubTranscriptFormatterReplayOptions(BaseModel):
    """Typed Sir Convert `transcript_formatter_replay_v1` options."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transcript_formatter_replay_v1"] = "transcript_formatter_replay_v1"
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat] = Field(
        min_length=1,
        max_length=4,
    )
    speaker_label_overrides: list[ConversionHubTranscriptSpeakerOverlayEntry] = Field(
        min_length=1,
        max_length=128,
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


class ConversionHubTranscriptFormatterReplayJobSpec(BaseModel):
    """Strict Sir Convert v2 JobSpec for `transcript_json -> transcript_bundle`."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    source: ConversionHubTranscriptFormatterReplaySource
    conversion: ConversionHubTranscriptFormatterReplayConversion
    transcript_formatter_options: ConversionHubTranscriptFormatterReplayOptions
    retention: ConversionHubTranscriptFormatterReplayRetention


class ConversionHubTranscriptFormatterReplayPrepareRequest(BaseModel):
    """Request overlay-aware formatter replay for selected artifact formats."""

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


class ConversionHubTranscriptFormatterReplayPrepareResponse(BaseModel):
    """Prepared replay payload for the HuleEdu Sir Convert Gateway client."""

    model_config = ConfigDict(extra="forbid")

    transcript_id: UUID
    correlation_id: str
    idempotency_key: str
    gateway_filename: str
    content_type: Literal["application/json"] = "application/json"
    transcript_json: dict[str, JsonValue]
    job_spec: ConversionHubTranscriptFormatterReplayJobSpec


class ConversionHubTranscriptFormatterReplayCompleteRequest(BaseModel):
    """Record a successfully parsed producer replay response."""

    model_config = ConfigDict(extra="forbid")

    sir_convert_job_id: str = Field(min_length=1, max_length=255)
    correlation_id: str | None = Field(default=None, max_length=128)
    status: Literal["succeeded"]
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat] = Field(
        min_length=1,
        max_length=4,
    )
    result: dict[str, JsonValue]
    artifact_manifest: dict[str, JsonValue]

    @field_validator("requested_artifacts")
    @classmethod
    def _requested_artifacts_are_unique(
        cls,
        value: list[ConversionHubTranscriptFormatterArtifactFormat],
    ) -> list[ConversionHubTranscriptFormatterArtifactFormat]:
        if len(set(value)) != len(value):
            raise ValueError("requested_artifacts must be unique")
        return value


class ConversionHubTranscriptFormatterArtifactRef(BaseModel):
    """Producer-owned named replay artifact reference."""

    model_config = ConfigDict(extra="forbid")

    requested_artifact: ConversionHubTranscriptFormatterArtifactFormat
    artifact_key: ConversionHubTranscriptFormatterArtifactKey
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=1)
    retrieval_path: str = Field(min_length=1)


class ConversionHubTranscriptFormatterReplayResponse(BaseModel):
    """Replay provenance and available producer artifact references."""

    model_config = ConfigDict(extra="forbid")

    transcript_id: UUID
    conversion_hub_job_id: UUID
    sir_convert_job_id: str
    correlation_id: str | None
    status: Literal["succeeded"] = "succeeded"
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat]
    artifacts: list[ConversionHubTranscriptFormatterArtifactRef]
