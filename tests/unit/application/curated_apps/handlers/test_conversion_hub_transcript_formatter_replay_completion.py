"""Tests for Conversion Hub transcript formatter replay completion.

Domain purpose:
  Prove completed producer replay jobs persist local provenance and fail closed
  when saved-transcript or artifact manifests do not match.

Relationships:
  - Exercises `CompleteConversionHubTranscriptFormatterReplayHandler`.
  - Reuses replay fixture builders from the prepare/replay test module.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterReplayCompleteRequest,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay as transcript_replay_handlers,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers import (
    test_conversion_hub_transcript_formatter_replay as replay_fixtures,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedClock,
    FixedIdGenerator,
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
    SequentialIdGenerator,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_persists_local_job_and_returns_requested_artifact_refs() -> None:
    actor = make_user()
    transcript_id = uuid4()
    job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    jobs = InMemoryConversionHubJobRepository()
    artifacts = replay_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    artifact_txt_id = uuid4()
    artifact_md_id = uuid4()
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(now=replay_fixtures._now())
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(replay_fixtures._now()),
        id_generator=SequentialIdGenerator([job_id, artifact_txt_id, artifact_md_id]),
    )

    result = await handler.handle(
        actor=actor,
        authenticated_huleedu_subject="teacher-subject-1",
        transcript_id=transcript_id,
        request=_complete_request(receipt_authority=receipt_authority),
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
        created_at=replay_fixtures._now(),
        updated_at=replay_fixtures._now(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_existing_replay_job_for_different_transcript() -> None:
    actor = make_user()
    transcript_a_id = uuid4()
    transcript_b_id = uuid4()
    existing_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_a_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_a_id,
    )
    transcripts.records[transcript_b_id] = replay_fixtures._saved_transcript(
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
        created_at=replay_fixtures._now(),
        updated_at=replay_fixtures._now(),
    )
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(now=replay_fixtures._now())
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=replay_fixtures.InMemoryTranscriptFormatterArtifactRepository(),
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(replay_fixtures._now()),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-1",
            transcript_id=transcript_b_id,
            request=_complete_request(
                correlation_id="corr-replay-b",
                receipt_authority=receipt_authority,
            ),
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert len(jobs.jobs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_missing_requested_artifact_receipts() -> None:
    actor = make_user()
    transcript_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(now=replay_fixtures._now())
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=InMemoryConversionHubJobRepository(),
        transcripts=transcripts,
        artifacts=replay_fixtures.InMemoryTranscriptFormatterArtifactRepository(),
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(replay_fixtures._now()),
        id_generator=FixedIdGenerator(uuid4()),
    )
    txt_only_payloads = [
        receipt_authority.artifact_payload(
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            filename="transcript_txt.txt",
            content_type="text/plain",
            content=replay_fixtures._TXT_CONTENT,
        )
    ]

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-1",
            transcript_id=transcript_id,
            request=_complete_request(
                receipt_authority=receipt_authority,
                artifact_payloads=txt_only_payloads,
            ),
        )
    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def _complete_request(
    *,
    correlation_id: str = "corr-replay-1",
    receipt_authority: replay_fixtures.SignedArtifactReceiptAuthority,
    artifact_payloads: list[dict[str, object]] | None = None,
) -> ConversionHubTranscriptFormatterReplayCompleteRequest:
    return ConversionHubTranscriptFormatterReplayCompleteRequest(
        sir_convert_job_id="sir-replay-job-1",
        correlation_id=correlation_id,
        status="succeeded",
        requested_artifacts=["txt", "md"],
        result=replay_fixtures._result(),
        artifact_payloads=artifact_payloads
        or replay_fixtures._artifact_payloads(receipt_authority),
    )
