"""Domain purpose: prove replay requests; relationships: replay handlers and repos."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

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
    ConversionHubTranscriptFormatterReplayCompleteRequest,
    ConversionHubTranscriptFormatterReplayPrepareRequest,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay as transcript_replay_handlers,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedClock,
    FixedIdGenerator,
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
    InMemoryTranscriptSpeakerOverlayRepository,
    SequentialIdGenerator,
)


def _now() -> datetime:
    return datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


class InMemoryTranscriptFormatterArtifactRepository:
    def __init__(self) -> None:
        self.records: dict[
            tuple[UUID, UUID, ConversionHubTranscriptFormatterArtifactKey],
            (ConversionHubTranscriptFormatterArtifactRecord),
        ] = {}

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
        self.records = {
            key: record
            for key, record in self.records.items()
            if not (record.owner_user_id == owner_user_id and record.transcript_id == transcript_id)
        }


def _saved_transcript(*, owner_user_id: UUID, transcript_id: UUID) -> ConversionHubSavedTranscript:
    return ConversionHubSavedTranscript(
        id=transcript_id,
        owner_user_id=owner_user_id,
        conversion_hub_job_id=uuid4(),
        sir_convert_job_id="sir-transcript-job-1",
        artifact_key="transcript_json",
        source_filename="seminarium.m4a",
        transcript_schema_version="transcript_json_v1",
        language_code="sv",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=_now(),
        correlation_id="corr-transcript-1",
        transcript_json={
            "schema_version": "transcript_json_v1",
            "transcript": {
                "text": "Hej från seminariet.",
                "segments": [
                    {
                        "id": "seg_1",
                        "start_seconds": 0,
                        "end_seconds": 2,
                        "speaker_label": "SPEAKER_00",
                        "text": "Hej från seminariet.",
                    },
                    {
                        "id": "seg_2",
                        "start_seconds": 3,
                        "end_seconds": 4,
                        "speaker_label": "SPEAKER_01",
                        "text": "Välkomna.",
                    },
                ],
            },
            "diarization": {"status": "succeeded"},
        },
        created_at=_now(),
        updated_at=_now(),
    )


def _overlay(
    *,
    owner_user_id: UUID,
    transcript_id: UUID,
    canonical_speaker_label: str,
    display_name: str,
) -> ConversionHubTranscriptSpeakerOverlay:
    return ConversionHubTranscriptSpeakerOverlay(
        id=uuid4(),
        owner_user_id=owner_user_id,
        transcript_id=transcript_id,
        canonical_speaker_label=canonical_speaker_label,
        display_name=display_name,
        created_at=_now(),
        updated_at=_now(),
    )


def _manifest(*, job_id: str = "sir-replay-job-1") -> dict[str, object]:
    return {
        "api_version": "v2",
        "job_id": job_id,
        "output_format": "transcript_bundle",
        "artifacts": [
            {
                "artifact_key": "transcript_txt",
                "availability": "available",
                "content_type": "text/plain",
                "filename": "transcript_txt.txt",
                "size_bytes": 128,
                "sha256": "a" * 64,
                "retrieval_path": f"/v2/convert/jobs/{job_id}/artifacts/transcript_txt",
            },
            {
                "artifact_key": "transcript_md",
                "availability": "available",
                "content_type": "text/markdown",
                "filename": "transcript_md.md",
                "size_bytes": 256,
                "sha256": "b" * 64,
                "retrieval_path": f"/v2/convert/jobs/{job_id}/artifacts/transcript_md",
            },
        ],
    }


def _manifest_artifacts(manifest: dict[str, object]) -> list[object]:
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    return artifacts


def _result(*, job_id: str = "sir-replay-job-1") -> dict[str, object]:
    return {
        "api_version": "v2",
        "job_id": job_id,
        "status": "succeeded",
        "result": {
            "artifact": {
                "filename": "transcript_replay_bundle_manifest.json",
                "format": "transcript_bundle",
                "content_type": "application/json",
                "size_bytes": 512,
                "sha256": "c" * 64,
            },
            "conversion_metadata": {
                "pipeline_used": "transcript_json_to_transcript_bundle_replay_v2",
                "backend_used": None,
                "acceleration_used": None,
                "options_fingerprint": "sha256:replay",
            },
            "warnings": [],
        },
    }


async def _seed_transcript_with_overlays(
    *,
    owner_id: UUID,
    transcript_id: UUID,
    transcripts: InMemorySavedTranscriptRepository,
    overlays: InMemoryTranscriptSpeakerOverlayRepository,
) -> None:
    transcripts.records[transcript_id] = _saved_transcript(
        owner_user_id=owner_id,
        transcript_id=transcript_id,
    )
    await overlays.replace_for_transcript(
        owner_user_id=owner_id,
        transcript_id=transcript_id,
        overlays=[
            _overlay(
                owner_user_id=owner_id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_00",
                display_name="Anna Andersson",
            ),
            _overlay(
                owner_user_id=owner_id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_01",
                display_name="Bo Berg",
            ),
        ],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_replay_builds_strict_gateway_job_spec_from_saved_overlay() -> None:
    actor = make_user()
    transcript_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    replay_correlation_id = uuid4()
    await _seed_transcript_with_overlays(
        owner_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )
    handler = transcript_replay_handlers.PrepareConversionHubTranscriptFormatterReplayHandler(
        transcripts=transcripts,
        speaker_overlays=overlays,
        uow=FakeUow(),
        id_generator=FixedIdGenerator(replay_correlation_id),
    )

    prepared = await handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterReplayPrepareRequest(
            requested_artifacts=["txt", "md"]
        ),
        correlation_id=None,
    )

    assert prepared.correlation_id == (
        f"corr_skriptoteket_transcript_replay_{replay_correlation_id}"
    )
    assert prepared.content_type == "application/json"
    assert prepared.gateway_filename == f"saved-transcript-{transcript_id}.json"
    assert prepared.job_spec.source.format == "transcript_json"
    assert prepared.job_spec.conversion.output_format == "transcript_bundle"
    assert prepared.job_spec.transcript_formatter_options.schema_version == (
        "transcript_formatter_replay_v1"
    )
    assert prepared.job_spec.transcript_formatter_options.requested_artifacts == ["txt", "md"]
    assert [
        entry.model_dump()
        for entry in prepared.job_spec.transcript_formatter_options.speaker_label_overrides
    ] == [
        {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna Andersson"},
        {"canonical_speaker_label": "SPEAKER_01", "display_name": "Bo Berg"},
    ]
    assert prepared.job_spec.retention.pin is False
    assert prepared.transcript_json == transcripts.records[transcript_id].transcript_json


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_replay_rejects_missing_overlay_without_canonical_label_fallback() -> None:
    actor = make_user()
    transcript_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = _saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    handler = transcript_replay_handlers.PrepareConversionHubTranscriptFormatterReplayHandler(
        transcripts=transcripts,
        speaker_overlays=InMemoryTranscriptSpeakerOverlayRepository(),
        uow=FakeUow(),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            transcript_id=transcript_id,
            request=ConversionHubTranscriptFormatterReplayPrepareRequest(),
            correlation_id="corr-replay-1",
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_persists_local_job_and_returns_requested_artifact_refs() -> None:
    actor = make_user()
    transcript_id = uuid4()
    job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = _saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    jobs = InMemoryConversionHubJobRepository()
    artifacts = InMemoryTranscriptFormatterArtifactRepository()
    artifact_txt_id = uuid4()
    artifact_md_id = uuid4()
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        uow=FakeUow(),
        clock=FixedClock(_now()),
        id_generator=SequentialIdGenerator([job_id, artifact_txt_id, artifact_md_id]),
    )

    result = await handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterReplayCompleteRequest(
            sir_convert_job_id="sir-replay-job-1",
            correlation_id="corr-replay-1",
            status="succeeded",
            requested_artifacts=["txt", "md"],
            result=_result(),
            artifact_manifest=_manifest(),
        ),
    )

    assert result.conversion_hub_job_id == job_id
    assert [artifact.artifact_key for artifact in result.artifacts] == [
        "transcript_txt",
        "transcript_md",
    ]
    assert sorted(record.id for record in artifacts.records.values()) == sorted(
        [artifact_txt_id, artifact_md_id]
    )
    persisted_txt = artifacts.records[
        (actor.id, transcript_id, ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT)
    ]
    assert persisted_txt.conversion_hub_job_id == job_id
    assert persisted_txt.sir_convert_job_id == "sir-replay-job-1"
    assert persisted_txt.retrieval_path == (
        "/v2/convert/jobs/sir-replay-job-1/artifacts/transcript_txt"
    )
    assert jobs.jobs[job_id] == ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename=f"saved-transcript-{transcript_id}.json",
        source_format=ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
        output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
        pdf_layout=None,
        upstream_job_id="sir-replay-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-replay-1",
        error_message=None,
        created_at=_now(),
        updated_at=_now(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_existing_replay_job_for_different_transcript() -> None:
    actor = make_user()
    transcript_a_id = uuid4()
    transcript_b_id = uuid4()
    existing_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_a_id] = _saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_a_id,
    )
    transcripts.records[transcript_b_id] = _saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_b_id,
    )
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[existing_job_id] = ConversionHubJob(
        id=existing_job_id,
        owner_user_id=actor.id,
        input_filename=f"saved-transcript-{transcript_a_id}.json",
        source_format=ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
        output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
        pdf_layout=None,
        upstream_job_id="sir-replay-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-replay-a",
        error_message=None,
        created_at=_now(),
        updated_at=_now(),
    )
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=InMemoryTranscriptFormatterArtifactRepository(),
        uow=FakeUow(),
        clock=FixedClock(_now()),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            transcript_id=transcript_b_id,
            request=ConversionHubTranscriptFormatterReplayCompleteRequest(
                sir_convert_job_id="sir-replay-job-1",
                correlation_id="corr-replay-b",
                status="succeeded",
                requested_artifacts=["txt", "md"],
                result=_result(),
                artifact_manifest=_manifest(),
            ),
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert len(jobs.jobs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_unknown_or_missing_requested_artifacts() -> None:
    actor = make_user()
    transcript_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = _saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=InMemoryConversionHubJobRepository(),
        transcripts=transcripts,
        artifacts=InMemoryTranscriptFormatterArtifactRepository(),
        uow=FakeUow(),
        clock=FixedClock(_now()),
        id_generator=FixedIdGenerator(uuid4()),
    )
    malformed = _manifest()
    malformed_artifacts = _manifest_artifacts(malformed)
    malformed["artifacts"] = [
        *malformed_artifacts,
        {"artifact_key": "transcript_json", "availability": "available"},
    ]
    missing = _manifest()
    missing["artifacts"] = [_manifest_artifacts(missing)[0]]

    for manifest in [
        malformed,
        missing,
    ]:
        with pytest.raises(DomainError) as exc:
            await handler.handle(
                actor=actor,
                transcript_id=transcript_id,
                request=ConversionHubTranscriptFormatterReplayCompleteRequest(
                    sir_convert_job_id="sir-replay-job-1",
                    correlation_id="corr-replay-1",
                    status="succeeded",
                    requested_artifacts=["txt", "md"],
                    result=_result(),
                    artifact_manifest=manifest,
                ),
            )
        assert exc.value.code is ErrorCode.SERVICE_UNAVAILABLE
