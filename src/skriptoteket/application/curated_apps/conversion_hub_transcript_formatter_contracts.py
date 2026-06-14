"""Conversion Hub transcript formatter producer contracts.

Domain purpose:
  Define the strict Sir Convert transcript formatter JobSpec and named artifact
  descriptors used by Skriptoteket-owned formatter export workflows.

Relationships:
  - Built by `handlers.conversion_hub_transcript_formatter_exports`.
  - Validated by `handlers.conversion_hub_transcript_formatter_export_parsing`.
  - Persisted through transcript formatter artifact repositories and actions.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubTranscriptSpeakerOverlayEntry,
)

TRANSCRIPT_FORMATTER_EXPORT_ARTIFACT_MAX_BYTES = 4 * 1024 * 1024
TRANSCRIPT_FORMATTER_EXPORT_TOTAL_ARTIFACT_MAX_BYTES = 8 * 1024 * 1024


class ConversionHubTranscriptFormatterArtifactFormat(StrEnum):
    """Closed artifact format values accepted by Sir Convert formatter exports."""

    TXT = "txt"
    MD = "md"
    VTT = "vtt"
    SRT = "srt"


class ConversionHubTranscriptFormatterArtifactKey(StrEnum):
    """Closed named formatter artifact keys returned by Sir Convert."""

    TRANSCRIPT_TXT = "transcript_txt"
    TRANSCRIPT_MD = "transcript_md"
    TRANSCRIPT_VTT = "transcript_vtt"
    TRANSCRIPT_SRT = "transcript_srt"


class ConversionHubTranscriptFormatterExportSource(BaseModel):
    """Formatter source descriptor for the uploaded canonical transcript JSON file."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["upload"] = "upload"
    filename: Literal["saved-transcript.json"] = "saved-transcript.json"
    format: Literal["transcript_json"] = "transcript_json"


class ConversionHubTranscriptFormatterExportConversion(BaseModel):
    """Formatter conversion target descriptor."""

    model_config = ConfigDict(extra="forbid")

    output_format: Literal["transcript_bundle"] = "transcript_bundle"


class ConversionHubTranscriptFormatterExportRetention(BaseModel):
    """Formatter export retention descriptor; transcript exports are never pinned."""

    model_config = ConfigDict(extra="forbid")

    pin: Literal[False] = False


class ConversionHubTranscriptFormatterExportOptions(BaseModel):
    """Typed Sir Convert formatter options."""

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


class ConversionHubTranscriptFormatterExportJobSpec(BaseModel):
    """Strict Sir Convert v2 JobSpec for `transcript_json -> transcript_bundle`."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    source: ConversionHubTranscriptFormatterExportSource
    conversion: ConversionHubTranscriptFormatterExportConversion
    transcript_formatter_options: ConversionHubTranscriptFormatterExportOptions
    retention: ConversionHubTranscriptFormatterExportRetention


class ConversionHubTranscriptFormatterArtifactRef(BaseModel):
    """Producer-owned named formatter artifact reference."""

    model_config = ConfigDict(extra="forbid")

    requested_artifact: ConversionHubTranscriptFormatterArtifactFormat
    artifact_key: ConversionHubTranscriptFormatterArtifactKey
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=1, max_length=128)
    retrieval_path: str = Field(min_length=1, max_length=500)
