"""Conversion Hub durable transcript save and overlay contracts.

Domain purpose:
  Define the owner-scoped canonical transcript JSON persistence boundary for
  Conversion Hub plus speaker display-name overlays so downstream transcript
  management can consume stable saved transcripts after the Sir Convert
  artifact TTL expires without rewriting canonical JSON truth.

Relationships:
  - Consumed by `handlers.conversion_hub_transcript_saves`.
  - Serialized by `web.api.v1.apps_conversion_hub_transcript_saves`.
  - Persisted through Conversion Hub transcript repository protocols.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class SaveConversionHubTranscriptRequest(BaseModel):
    """Request to save one Sir Convert transcript JSON artifact."""

    model_config = ConfigDict(extra="forbid")

    sir_convert_job_id: str = Field(min_length=1, max_length=255)
    artifact_key: str = Field(min_length=1, max_length=128)
    source_filename: str = Field(min_length=1, max_length=255)
    transcript_json: dict[str, JsonValue]
    transcript_schema_version: str = Field(min_length=1, max_length=64)
    language_code: str | None = Field(default=None, max_length=16)
    diarization_mode: str = Field(min_length=1, max_length=64)
    speaker_count: int | None = Field(default=None, ge=1)
    speaker_min: int | None = Field(default=None, ge=1)
    speaker_max: int | None = Field(default=None, ge=1)
    generated_at: datetime | None = None
    correlation_id: str | None = Field(default=None, max_length=128)


class ConversionHubSavedTranscript(BaseModel):
    """Persisted canonical transcript JSON with owner and provenance metadata."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    conversion_hub_job_id: UUID
    sir_convert_job_id: str
    artifact_key: str
    source_filename: str
    transcript_schema_version: str
    language_code: str | None = None
    diarization_mode: str
    speaker_count: int | None = None
    speaker_min: int | None = None
    speaker_max: int | None = None
    generated_at: datetime | None = None
    correlation_id: str | None = None
    transcript_json: dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime


class ConversionHubSavedTranscriptResponse(BaseModel):
    """API response for a saved transcript record."""

    model_config = ConfigDict(extra="forbid")

    transcript_id: UUID
    owner_user_id: UUID
    conversion_hub_job_id: UUID
    sir_convert_job_id: str
    artifact_key: str
    source_filename: str
    transcript_schema_version: str
    language_code: str | None
    diarization_mode: str
    speaker_count: int | None
    speaker_min: int | None
    speaker_max: int | None
    generated_at: datetime | None
    correlation_id: str | None
    transcript_json: dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(
        cls, record: ConversionHubSavedTranscript
    ) -> "ConversionHubSavedTranscriptResponse":
        """Build a transport response from a saved transcript aggregate."""
        return cls(
            transcript_id=record.id,
            owner_user_id=record.owner_user_id,
            conversion_hub_job_id=record.conversion_hub_job_id,
            sir_convert_job_id=record.sir_convert_job_id,
            artifact_key=record.artifact_key,
            source_filename=record.source_filename,
            transcript_schema_version=record.transcript_schema_version,
            language_code=record.language_code,
            diarization_mode=record.diarization_mode,
            speaker_count=record.speaker_count,
            speaker_min=record.speaker_min,
            speaker_max=record.speaker_max,
            generated_at=record.generated_at,
            correlation_id=record.correlation_id,
            transcript_json=record.transcript_json,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ConversionHubTranscriptSpeakerOverlayEntry(BaseModel):
    """One display-name overlay for a canonical transcript speaker label."""

    model_config = ConfigDict(extra="forbid")

    canonical_speaker_label: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class UpdateConversionHubTranscriptSpeakerOverlaysRequest(BaseModel):
    """Replace the editable speaker-name overlays for one saved transcript."""

    model_config = ConfigDict(extra="forbid")

    overlays: list[ConversionHubTranscriptSpeakerOverlayEntry] = Field(
        default_factory=list,
        max_length=128,
    )


class ConversionHubTranscriptSpeakerOverlay(BaseModel):
    """Persisted owner-scoped display-name overlay for one speaker label."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    owner_user_id: UUID
    transcript_id: UUID
    canonical_speaker_label: str
    display_name: str
    created_at: datetime
    updated_at: datetime


class ConversionHubTranscriptSpeakerOverlaysResponse(BaseModel):
    """API response containing display-name overlays for a saved transcript."""

    model_config = ConfigDict(extra="forbid")

    transcript_id: UUID
    overlays: list[ConversionHubTranscriptSpeakerOverlayEntry]
    updated_at: datetime | None = None

    @classmethod
    def from_domain(
        cls,
        *,
        transcript_id: UUID,
        overlays: list[ConversionHubTranscriptSpeakerOverlay],
    ) -> "ConversionHubTranscriptSpeakerOverlaysResponse":
        """Build a transport response from persisted overlay rows."""
        return cls(
            transcript_id=transcript_id,
            overlays=[
                ConversionHubTranscriptSpeakerOverlayEntry(
                    canonical_speaker_label=overlay.canonical_speaker_label,
                    display_name=overlay.display_name,
                )
                for overlay in overlays
            ],
            updated_at=max((overlay.updated_at for overlay in overlays), default=None),
        )
