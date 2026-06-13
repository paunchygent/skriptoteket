"""Tests for durable Conversion Hub transcript save handlers.

Domain purpose:
  Prove owner-scoped canonical transcript JSON persistence before downstream
  transcript management or formatter work consumes saved transcript records.

Relationships:
  - Exercises `handlers.conversion_hub_transcript_saves` through repository
    protocols.
  - Complements web API and frontend tests for PR-0343.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubSavedTranscriptResponse,
    ConversionHubTranscriptSpeakerOverlay,
    SaveConversionHubTranscriptRequest,
    UpdateConversionHubTranscriptSpeakerOverlaysRequest,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_transcript_saves import (
    GetConversionHubTranscriptHandler,
    ListConversionHubTranscriptSpeakerOverlaysHandler,
    SaveConversionHubTranscriptHandler,
    UpdateConversionHubTranscriptSpeakerOverlaysHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user


class InMemoryConversionHubJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ConversionHubJob] = {}

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        return self.jobs.get(job_id)

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        for job in self.jobs.values():
            if job.upstream_job_id == upstream_job_id:
                return job
        return None

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


class InMemorySavedTranscriptRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, ConversionHubSavedTranscript] = {}

    async def create(
        self,
        *,
        record: ConversionHubSavedTranscript,
    ) -> ConversionHubSavedTranscript:
        self.records[record.id] = record
        return record

    async def get_by_owner_and_id(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript | None:
        record = self.records.get(transcript_id)
        if record is None or record.owner_user_id != owner_user_id:
            return None
        return record

    async def get_by_owner_and_upstream_job(
        self,
        *,
        owner_user_id: UUID,
        sir_convert_job_id: str,
    ) -> ConversionHubSavedTranscript | None:
        for record in self.records.values():
            if (
                record.owner_user_id == owner_user_id
                and record.sir_convert_job_id == sir_convert_job_id
            ):
                return record
        return None


class InMemoryTranscriptSpeakerOverlayRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, ConversionHubTranscriptSpeakerOverlay] = {}

    async def list_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> list[ConversionHubTranscriptSpeakerOverlay]:
        return sorted(
            [
                overlay
                for overlay in self.records.values()
                if overlay.owner_user_id == owner_user_id and overlay.transcript_id == transcript_id
            ],
            key=lambda overlay: overlay.canonical_speaker_label,
        )

    async def replace_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        overlays: list[ConversionHubTranscriptSpeakerOverlay],
    ) -> list[ConversionHubTranscriptSpeakerOverlay]:
        self.records = {
            overlay_id: overlay
            for overlay_id, overlay in self.records.items()
            if not (
                overlay.owner_user_id == owner_user_id and overlay.transcript_id == transcript_id
            )
        }
        for overlay in overlays:
            self.records[overlay.id] = overlay
        return await self.list_for_transcript(
            owner_user_id=owner_user_id,
            transcript_id=transcript_id,
        )


class InMemoryTranscriptFormatterArtifactRepository:
    def __init__(self) -> None:
        self.records: dict[
            tuple[UUID, UUID, ConversionHubTranscriptFormatterArtifactKey],
            ConversionHubTranscriptFormatterArtifactRecord,
        ] = {}
        self.delete_calls: list[tuple[UUID, UUID]] = []

    async def replace_for_replay(
        self,
        *,
        records: list[ConversionHubTranscriptFormatterArtifactRecord],
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
        if not records:
            return []
        owner_user_id = records[0].owner_user_id
        transcript_id = records[0].transcript_id
        await self.delete_for_transcript(
            owner_user_id=owner_user_id,
            transcript_id=transcript_id,
        )
        for record in records:
            self.records[(record.owner_user_id, record.transcript_id, record.artifact_key)] = record
        return records

    async def get_by_owner_transcript_and_key(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    ) -> ConversionHubTranscriptFormatterArtifactRecord | None:
        return self.records.get((owner_user_id, transcript_id, artifact_key))

    async def delete_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> None:
        self.delete_calls.append((owner_user_id, transcript_id))
        self.records = {
            key: record
            for key, record in self.records.items()
            if not (record.owner_user_id == owner_user_id and record.transcript_id == transcript_id)
        }


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value


class FixedIdGenerator:
    def __init__(self, value: UUID) -> None:
        self._value = value

    def new_uuid(self) -> UUID:
        return self._value


class SequentialIdGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self._values = values
        self._index = 0

    def new_uuid(self) -> UUID:
        value = self._values[self._index]
        self._index += 1
        return value


def _job(*, owner_user_id: UUID, job_id: UUID) -> ConversionHubJob:
    now = datetime(2026, 6, 12, tzinfo=timezone.utc)
    return ConversionHubJob(
        id=job_id,
        owner_user_id=owner_user_id,
        input_filename="seminarium.m4a",
        source_format=ConversionHubSourceFormatV2.AUDIO,
        output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
        upstream_job_id="sir-transcript-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-transcript-1",
        created_at=now,
        updated_at=now,
    )


def _transcript_json() -> dict[str, object]:
    return {
        "schema_version": "transcript_json_v1",
        "transcript": {
            "text": "Hej från seminariet.",
            "segments": [
                {
                    "id": "seg_1",
                    "start_seconds": 0.0,
                    "end_seconds": 2.4,
                    "speaker_label": "SPEAKER_00",
                    "text": "Hej från seminariet.",
                    "language": "sv",
                },
                {
                    "id": "seg_2",
                    "start_seconds": 2.5,
                    "end_seconds": 4.1,
                    "speaker_label": "SPEAKER_01",
                    "text": "Välkomna.",
                    "language": "sv",
                },
            ],
        },
        "language": {"detected": "sv", "confidence": 0.98},
        "diarization": {
            "mode_requested": "known_speaker_count",
            "mode_used": "known_speaker_count",
        },
        "runtime": {"generated_at": "2026-06-12T10:00:00Z"},
    }


def _request() -> SaveConversionHubTranscriptRequest:
    return SaveConversionHubTranscriptRequest(
        sir_convert_job_id="sir-transcript-job-1",
        artifact_key="transcript_json",
        source_filename="seminarium.m4a",
        transcript_json=_transcript_json(),
        transcript_schema_version="transcript_json_v1",
        language_code="sv",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-transcript-1",
    )


def _first_segment_speaker_label(record: ConversionHubSavedTranscriptResponse) -> str:
    transcript = record.transcript_json["transcript"]
    assert isinstance(transcript, dict)
    segments = transcript["segments"]
    assert isinstance(segments, list)
    first_segment = segments[0]
    assert isinstance(first_segment, dict)
    speaker_label = first_segment["speaker_label"]
    assert isinstance(speaker_label, str)
    return speaker_label


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_transcript_persists_owner_scoped_record_with_provenance() -> None:
    actor = make_user()
    job_id = uuid4()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    transcripts = InMemorySavedTranscriptRepository()
    save = SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=transcripts,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(transcript_id),
    )
    get = GetConversionHubTranscriptHandler(
        transcripts=transcripts,
        uow=FakeUow(),
    )

    result = await save.handle(actor=actor, conversion_hub_job_id=job_id, request=_request())
    readback = await get.handle(actor=actor, transcript_id=result.transcript_id)

    assert result.transcript_id == transcript_id
    assert result.sir_convert_job_id == "sir-transcript-job-1"
    assert result.transcript_schema_version == "transcript_json_v1"
    assert result.diarization_mode == "known_speaker_count"
    assert _first_segment_speaker_label(readback) == "SPEAKER_00"
    assert readback.source_filename == "seminarium.m4a"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_speaker_overlays_persists_names_without_rewriting_json() -> None:
    actor = make_user()
    job_id = uuid4()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    save = SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=transcripts,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(transcript_id),
    )
    await save.handle(actor=actor, conversion_hub_job_id=job_id, request=_request())
    original_json = transcripts.records[transcript_id].transcript_json
    formatter_artifacts = InMemoryTranscriptFormatterArtifactRepository()
    update = UpdateConversionHubTranscriptSpeakerOverlaysHandler(
        transcripts=transcripts,
        speaker_overlays=overlays,
        formatter_artifacts=formatter_artifacts,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 11, 0, tzinfo=timezone.utc)),
        id_generator=SequentialIdGenerator([uuid4(), uuid4()]),
    )

    result = await update.handle(
        actor=actor,
        transcript_id=transcript_id,
        request=UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[
                {
                    "canonical_speaker_label": "SPEAKER_00",
                    "display_name": "  Anna Andersson  ",
                },
                {
                    "canonical_speaker_label": "SPEAKER_01",
                    "display_name": "Bo Berg",
                },
            ]
        ),
    )

    assert result.transcript_id == transcript_id
    assert [overlay.display_name for overlay in result.overlays] == ["Anna Andersson", "Bo Berg"]
    assert transcripts.records[transcript_id].transcript_json == original_json
    assert formatter_artifacts.delete_calls == [(actor.id, transcript_id)]

    listed = await ListConversionHubTranscriptSpeakerOverlaysHandler(
        transcripts=transcripts,
        speaker_overlays=overlays,
        uow=FakeUow(),
    ).handle(actor=actor, transcript_id=transcript_id)
    assert [overlay.canonical_speaker_label for overlay in listed.overlays] == [
        "SPEAKER_00",
        "SPEAKER_01",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_speaker_overlays_rejects_invalid_overlay_input() -> None:
    actor = make_user()
    job_id = uuid4()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    transcripts = InMemorySavedTranscriptRepository()
    save = SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=transcripts,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(transcript_id),
    )
    await save.handle(actor=actor, conversion_hub_job_id=job_id, request=_request())
    handler = UpdateConversionHubTranscriptSpeakerOverlaysHandler(
        transcripts=transcripts,
        speaker_overlays=InMemoryTranscriptSpeakerOverlayRepository(),
        formatter_artifacts=InMemoryTranscriptFormatterArtifactRepository(),
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 11, 0, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(uuid4()),
    )
    invalid_requests = [
        UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[{"canonical_speaker_label": "SPEAKER_99", "display_name": "Anna"}]
        ),
        UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[
                {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
                {"canonical_speaker_label": "SPEAKER_00", "display_name": "Bo"},
            ]
        ),
        UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[{"canonical_speaker_label": "SPEAKER_00", "display_name": "   "}]
        ),
        UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[
                {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
                {"canonical_speaker_label": "SPEAKER_01", "display_name": " anna "},
            ]
        ),
        UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[{"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna\n"}]
        ),
    ]

    for request in invalid_requests:
        with pytest.raises(DomainError) as exc:
            await handler.handle(actor=actor, transcript_id=transcript_id, request=request)
        assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_speaker_overlay_request_rejects_too_long_display_name() -> None:
    with pytest.raises(ValidationError):
        UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[
                {
                    "canonical_speaker_label": "SPEAKER_00",
                    "display_name": "A" * 121,
                }
            ]
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_speaker_overlays_fail_closed_for_other_owner() -> None:
    owner = make_user()
    other_user = make_user()
    job_id = uuid4()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=owner.id, job_id=job_id)
    transcripts = InMemorySavedTranscriptRepository()
    save = SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=transcripts,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(transcript_id),
    )
    await save.handle(actor=owner, conversion_hub_job_id=job_id, request=_request())
    handler = ListConversionHubTranscriptSpeakerOverlaysHandler(
        transcripts=transcripts,
        speaker_overlays=InMemoryTranscriptSpeakerOverlayRepository(),
        uow=FakeUow(),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=other_user, transcript_id=transcript_id)

    assert exc.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_transcript_rejects_json_without_segments() -> None:
    actor = make_user()
    job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    request = _request().model_copy(
        update={
            "transcript_json": {
                "schema_version": "transcript_json_v1",
                "transcript": {"text": "Hej.", "segments": []},
            }
        }
    )
    handler = SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=InMemorySavedTranscriptRepository(),
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=actor, conversion_hub_job_id=job_id, request=request)

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_transcript_fails_closed_for_other_owner() -> None:
    owner = make_user()
    other_user = make_user()
    job_id = uuid4()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=owner.id, job_id=job_id)
    transcripts = InMemorySavedTranscriptRepository()
    save = SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=transcripts,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(transcript_id),
    )
    await save.handle(actor=owner, conversion_hub_job_id=job_id, request=_request())
    handler = GetConversionHubTranscriptHandler(transcripts=transcripts, uow=FakeUow())

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=other_user, transcript_id=transcript_id)

    assert exc.value.code is ErrorCode.NOT_FOUND
