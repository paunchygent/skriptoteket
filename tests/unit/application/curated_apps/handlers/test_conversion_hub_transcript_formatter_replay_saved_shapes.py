"""Tests for saved transcript JSON shapes consumed by formatter replay.

Domain purpose:
  Prove transcript JSON variants accepted at durable save remain valid inputs
  for overlay-aware formatter replay preparation.

Relationships:
  - Exercises transcript save, speaker overlay persistence, and replay prepare
    handlers across the application-layer contract.
  - Reuses in-memory protocol fakes from transcript save handler tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterReplayPrepareRequest,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    SaveConversionHubTranscriptRequest,
    UpdateConversionHubTranscriptSpeakerOverlaysRequest,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay as replay_handlers,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_transcript_saves import (
    SaveConversionHubTranscriptHandler,
    UpdateConversionHubTranscriptSpeakerOverlaysHandler,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedClock,
    FixedIdGenerator,
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
    InMemoryTranscriptFormatterArtifactRepository,
    InMemoryTranscriptSpeakerOverlayRepository,
    SequentialIdGenerator,
    _job,
)


def _generated_at() -> datetime:
    return datetime(2026, 6, 13, 19, 48, tzinfo=timezone.utc)


def _top_level_segments_request() -> SaveConversionHubTranscriptRequest:
    return SaveConversionHubTranscriptRequest(
        sir_convert_job_id="sir-transcript-job-1",
        artifact_key="transcript_json",
        source_filename="english-dialogue-two-speakers.mp3",
        transcript_json={
            "schema_version": "transcript_json_v1",
            "transcript": {"text": "Hello from one speaker. Hello from another."},
            "segments": [
                {
                    "id": "seg_1",
                    "start_seconds": 0,
                    "end_seconds": 2,
                    "speaker_label": "SPEAKER_00",
                    "text": "Hello from one speaker.",
                },
                {
                    "id": "seg_2",
                    "start_seconds": 2,
                    "end_seconds": 4,
                    "speaker_label": "SPEAKER_01",
                    "text": "Hello from another.",
                },
            ],
            "diarization": {"status": "succeeded"},
        },
        transcript_schema_version="transcript_json_v1",
        language_code="en",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=_generated_at(),
        correlation_id="corr-transcript-live-proof",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_prepare_accepts_saved_top_level_segments_with_overlays() -> None:
    actor = make_user()
    job_id = uuid4()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[job_id] = _job(owner_user_id=actor.id, job_id=job_id)
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    await SaveConversionHubTranscriptHandler(
        jobs=jobs,
        transcripts=transcripts,
        uow=FakeUow(),
        clock=FixedClock(_generated_at()),
        id_generator=FixedIdGenerator(transcript_id),
    ).handle(
        actor=actor,
        conversion_hub_job_id=job_id,
        request=_top_level_segments_request(),
    )
    await UpdateConversionHubTranscriptSpeakerOverlaysHandler(
        transcripts=transcripts,
        speaker_overlays=overlays,
        formatter_artifacts=InMemoryTranscriptFormatterArtifactRepository(),
        uow=FakeUow(),
        clock=FixedClock(_generated_at()),
        id_generator=SequentialIdGenerator([uuid4(), uuid4()]),
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=UpdateConversionHubTranscriptSpeakerOverlaysRequest(
            overlays=[
                {"canonical_speaker_label": "SPEAKER_00", "display_name": "Alice"},
                {"canonical_speaker_label": "SPEAKER_01", "display_name": "Bob"},
            ]
        ),
    )

    prepared = await replay_handlers.PrepareConversionHubTranscriptFormatterReplayHandler(
        transcripts=transcripts,
        speaker_overlays=overlays,
        uow=FakeUow(),
        id_generator=FixedIdGenerator(uuid4()),
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterReplayPrepareRequest(
            requested_artifacts=["txt", "md", "vtt", "srt"]
        ),
        correlation_id="corr-replay-live-proof",
    )

    assert prepared.transcript_id == transcript_id
    assert prepared.correlation_id == "corr-replay-live-proof"
    assert prepared.transcript_json == transcripts.records[transcript_id].transcript_json
    assert [
        entry.model_dump()
        for entry in prepared.job_spec.transcript_formatter_options.speaker_label_overrides
    ] == [
        {"canonical_speaker_label": "SPEAKER_00", "display_name": "Alice"},
        {"canonical_speaker_label": "SPEAKER_01", "display_name": "Bob"},
    ]
