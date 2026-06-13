"""Conversion Hub durable transcript save handlers.

Domain purpose:
  Validate and persist canonical Sir Convert transcript JSON against an
  owner-scoped Conversion Hub job so transcript management can outlive upstream
  artifact retention without introducing formatter decisions.

Relationships:
  - Uses `ConversionHubJobRepositoryProtocol` for local job ownership checks.
  - Uses `ConversionHubSavedTranscriptRepositoryProtocol` for durable readback.
  - Returns `ConversionHubSavedTranscriptResponse` for the web boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from unicodedata import category as unicode_category
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubSavedTranscriptResponse,
    ConversionHubTranscriptSpeakerOverlay,
    ConversionHubTranscriptSpeakerOverlayEntry,
    ConversionHubTranscriptSpeakerOverlaysResponse,
    SaveConversionHubTranscriptRequest,
    UpdateConversionHubTranscriptSpeakerOverlaysRequest,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_transcript_json_contract import (
    canonical_speaker_labels,
    canonical_transcript_segments,
    string_value,
    transcript_mapping,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import (
    ConversionHubJobRepositoryProtocol,
    ConversionHubSavedTranscriptRepositoryProtocol,
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
    ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_TRANSCRIPT_ARTIFACT_KEY = "transcript_json"
_MAX_DISPLAY_NAME_LENGTH = 120


class SaveConversionHubTranscriptHandler:
    """Save one canonical transcript JSON artifact for the owning teacher."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._transcripts = transcripts
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        conversion_hub_job_id: UUID,
        request: SaveConversionHubTranscriptRequest,
    ) -> ConversionHubSavedTranscriptResponse:
        _validate_request_payload(request)
        async with self._uow:
            job = await self._load_owned_transcript_job(
                actor=actor,
                conversion_hub_job_id=conversion_hub_job_id,
                request=request,
            )
            existing = await self._transcripts.get_by_owner_and_upstream_job(
                owner_user_id=actor.id,
                sir_convert_job_id=request.sir_convert_job_id,
            )
            if existing is not None:
                return ConversionHubSavedTranscriptResponse.from_domain(existing)

            now = self._clock.now()
            record = await self._transcripts.create(
                record=ConversionHubSavedTranscript(
                    id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    conversion_hub_job_id=job.id,
                    sir_convert_job_id=request.sir_convert_job_id,
                    artifact_key=request.artifact_key,
                    source_filename=request.source_filename,
                    transcript_schema_version=request.transcript_schema_version,
                    language_code=request.language_code,
                    diarization_mode=request.diarization_mode,
                    speaker_count=request.speaker_count,
                    speaker_min=request.speaker_min,
                    speaker_max=request.speaker_max,
                    generated_at=request.generated_at,
                    correlation_id=request.correlation_id,
                    transcript_json=request.transcript_json,
                    created_at=now,
                    updated_at=now,
                )
            )
        return ConversionHubSavedTranscriptResponse.from_domain(record)

    async def _load_owned_transcript_job(
        self,
        *,
        actor: User,
        conversion_hub_job_id: UUID,
        request: SaveConversionHubTranscriptRequest,
    ) -> ConversionHubJob:
        job = await self._jobs.get_by_id(job_id=conversion_hub_job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("ConversionHubJob", str(conversion_hub_job_id))
        if job.upstream_job_id != request.sir_convert_job_id:
            raise validation_error("Transcript job provenance does not match the saved artifact.")
        if job.source_format is not ConversionHubSourceFormatV2.AUDIO:
            raise validation_error("Only transcript audio jobs can save transcript JSON.")
        if job.output_format is not ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE:
            raise validation_error("Only transcript bundle jobs can save transcript JSON.")
        if job.status is not ConversionHubJobStatus.SUCCEEDED:
            raise validation_error("Transcript job is not complete yet.")
        return job


class GetConversionHubTranscriptHandler:
    """Read one saved transcript record for the owning teacher."""

    def __init__(
        self,
        *,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._transcripts = transcripts
        self._uow = uow

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscriptResponse:
        async with self._uow:
            record = await self._transcripts.get_by_owner_and_id(
                owner_user_id=actor.id,
                transcript_id=transcript_id,
            )
        if record is None:
            raise not_found("ConversionHubSavedTranscript", str(transcript_id))
        return ConversionHubSavedTranscriptResponse.from_domain(record)


class ListConversionHubTranscriptSpeakerOverlaysHandler:
    """Read speaker display-name overlays for one saved transcript."""

    def __init__(
        self,
        *,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._transcripts = transcripts
        self._speaker_overlays = speaker_overlays
        self._uow = uow

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubTranscriptSpeakerOverlaysResponse:
        async with self._uow:
            transcript = await self._load_transcript(actor=actor, transcript_id=transcript_id)
            overlays = await self._speaker_overlays.list_for_transcript(
                owner_user_id=actor.id,
                transcript_id=transcript.id,
            )
        return ConversionHubTranscriptSpeakerOverlaysResponse.from_domain(
            transcript_id=transcript.id,
            overlays=overlays,
        )

    async def _load_transcript(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript:
        transcript = await self._transcripts.get_by_owner_and_id(
            owner_user_id=actor.id,
            transcript_id=transcript_id,
        )
        if transcript is None:
            raise not_found("ConversionHubSavedTranscript", str(transcript_id))
        return transcript


class UpdateConversionHubTranscriptSpeakerOverlaysHandler:
    """Replace speaker display-name overlays for one saved transcript."""

    def __init__(
        self,
        *,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        formatter_artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._transcripts = transcripts
        self._speaker_overlays = speaker_overlays
        self._formatter_artifacts = formatter_artifacts
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        request: UpdateConversionHubTranscriptSpeakerOverlaysRequest,
    ) -> ConversionHubTranscriptSpeakerOverlaysResponse:
        async with self._uow:
            transcript = await self._load_transcript(actor=actor, transcript_id=transcript_id)
            overlay_entries = _validate_overlay_entries(
                canonical_labels=canonical_speaker_labels(transcript.transcript_json),
                entries=request.overlays,
            )
            now = self._clock.now()
            overlays = await self._speaker_overlays.replace_for_transcript(
                owner_user_id=actor.id,
                transcript_id=transcript.id,
                overlays=[
                    ConversionHubTranscriptSpeakerOverlay(
                        id=self._id_generator.new_uuid(),
                        owner_user_id=actor.id,
                        transcript_id=transcript.id,
                        canonical_speaker_label=entry.canonical_speaker_label,
                        display_name=entry.display_name.strip(),
                        created_at=now,
                        updated_at=now,
                    )
                    for entry in overlay_entries
                ],
            )
            await self._formatter_artifacts.delete_for_transcript(
                owner_user_id=actor.id,
                transcript_id=transcript.id,
            )
        return ConversionHubTranscriptSpeakerOverlaysResponse.from_domain(
            transcript_id=transcript.id,
            overlays=overlays,
        )

    async def _load_transcript(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript:
        transcript = await self._transcripts.get_by_owner_and_id(
            owner_user_id=actor.id,
            transcript_id=transcript_id,
        )
        if transcript is None:
            raise not_found("ConversionHubSavedTranscript", str(transcript_id))
        return transcript


def _validate_request_payload(request: SaveConversionHubTranscriptRequest) -> None:
    if request.artifact_key != _TRANSCRIPT_ARTIFACT_KEY:
        raise validation_error("Only transcript_json artifacts can be saved here.")
    transcript_json = request.transcript_json
    schema_version = string_value(transcript_json, "schema_version") or string_value(
        transcript_json, "schemaVersion"
    )
    if schema_version != request.transcript_schema_version:
        raise validation_error("Transcript schema version does not match the JSON payload.")

    transcript = transcript_mapping(transcript_json)
    text = (
        string_value(transcript, "text")
        or string_value(transcript_json, "transcriptText")
        or string_value(transcript_json, "text")
    )
    if text is None or not text.strip():
        raise validation_error("Transcript JSON must contain transcript text.")

    for segment in canonical_transcript_segments(transcript_json):
        _validate_segment(segment)


def _validate_segment(segment: Mapping[str, JsonValue]) -> None:
    text = string_value(segment, "text")
    speaker = string_value(segment, "speaker_label") or string_value(segment, "speakerLabel")
    start = segment.get("start_seconds", segment.get("startSeconds"))
    end = segment.get("end_seconds", segment.get("endSeconds"))
    if text is None or not text.strip():
        raise validation_error("Transcript JSON segments must contain text.")
    if speaker is None or not speaker.strip():
        raise validation_error("Transcript JSON segments must contain speaker labels.")
    if not isinstance(start, int | float) or not isinstance(end, int | float):
        raise validation_error("Transcript JSON segments must contain numeric timestamps.")
    if float(end) < float(start):
        raise validation_error("Transcript JSON segment end must be after start.")


def _has_control_character(value: str) -> bool:
    return any(unicode_category(character).startswith("C") for character in value)


def _validate_overlay_entries(
    *,
    canonical_labels: list[str],
    entries: list[ConversionHubTranscriptSpeakerOverlayEntry],
) -> list[ConversionHubTranscriptSpeakerOverlayEntry]:
    canonical_label_set = set(canonical_labels)
    seen_labels: set[str] = set()
    seen_display_names: set[str] = set()
    normalized_entries: list[ConversionHubTranscriptSpeakerOverlayEntry] = []
    for entry in entries:
        label = entry.canonical_speaker_label
        display_name = entry.display_name.strip()
        if label in seen_labels:
            raise validation_error("Speaker overlay labels must be unique.")
        seen_labels.add(label)
        if label not in canonical_label_set:
            raise validation_error("Speaker overlay labels must exist in the saved transcript.")
        if not display_name:
            raise validation_error("Speaker display names must not be empty.")
        if len(display_name) > _MAX_DISPLAY_NAME_LENGTH:
            raise validation_error("Speaker display names are too long.")
        if _has_control_character(entry.display_name):
            raise validation_error("Speaker display names must not contain control characters.")
        display_key = display_name.casefold()
        if display_key in seen_display_names:
            raise validation_error("Speaker display names must be unique.")
        seen_display_names.add(display_key)
        normalized_entries.append(
            ConversionHubTranscriptSpeakerOverlayEntry(
                canonical_speaker_label=label,
                display_name=display_name,
            )
        )
    return normalized_entries
