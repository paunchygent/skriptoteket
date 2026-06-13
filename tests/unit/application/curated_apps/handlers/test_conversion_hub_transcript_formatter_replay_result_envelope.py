"""Tests for Conversion Hub transcript formatter replay result envelopes.

Domain purpose:
  Prove Sir Convert Service API v2 replay result envelopes can be completed
  into durable local replay job and artifact provenance without local exports.

Relationships:
  - Exercises `handlers.conversion_hub_transcript_formatter_replay`.
  - Complements the broader replay orchestration tests with live-shaped
    Service API v2 `/result` and `/artifacts` payloads.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import pytest

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
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
    SequentialIdGenerator,
)

_CONTENT_BY_KEY = {
    "transcript_txt": b"Anna: transcript text\n",
    "transcript_md": b"## Transcript\n\nAnna: transcript text\n",
    "transcript_vtt": b"WEBVTT\n\n00:00.000 --> 00:01.000\nAnna\n",
    "transcript_srt": b"1\n00:00:00,000 --> 00:00:01,000\nAnna\n",
}


def _service_result_envelope(*, job_id: str) -> dict[str, object]:
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
                "ocr_enabled": None,
                "ocr_engine_used": None,
                "ocr_languages_used": None,
                "acceleration_policy_requested": None,
                "gpu_runtime_kind": None,
                "gpu_device_count": None,
                "gpu_busy_percent": None,
                "gpu_memory_used_percent": None,
                "options_fingerprint": "sha256:replay",
                "template_id": None,
                "template_version": None,
                "template_artifact_sha256": None,
                "parallel_enabled": None,
                "max_chunk_workers": None,
                "chunk_size_pages": None,
                "effective_gpu_stage_limit": None,
                "scheduling_mode": None,
                "formula_authority": {},
            },
            "warnings": [],
        },
    }


def _four_artifact_payloads(
    *,
    receipt_authority: replay_fixtures.SignedArtifactReceiptAuthority,
    job_id: str,
) -> list[dict[str, object]]:
    content_type_by_key = {
        "transcript_txt": "text/plain",
        "transcript_md": "text/markdown",
        "transcript_vtt": "text/vtt",
        "transcript_srt": "application/x-subrip",
    }
    filename_by_key = {
        "transcript_txt": "transcript.txt",
        "transcript_md": "transcript.md",
        "transcript_vtt": "transcript.vtt",
        "transcript_srt": "transcript.srt",
    }
    return [
        receipt_authority.artifact_payload(
            artifact_key=ConversionHubTranscriptFormatterArtifactKey(artifact_key),
            filename=filename_by_key[artifact_key],
            content_type=content_type_by_key[artifact_key],
            content=content,
            job_id=job_id,
        )
        for artifact_key, content in _CONTENT_BY_KEY.items()
    ]


async def _assert_completion_rejects_result(
    *,
    result_payload: dict[str, object],
) -> None:
    actor = make_user()
    transcript_id = uuid4()
    sir_convert_job_id = "jobv2_replay_success"
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    artifacts = replay_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(now=replay_fixtures._now())
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=InMemoryConversionHubJobRepository(),
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(replay_fixtures._now()),
        id_generator=SequentialIdGenerator([uuid4(), uuid4(), uuid4(), uuid4(), uuid4()]),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-1",
            transcript_id=transcript_id,
            request=ConversionHubTranscriptFormatterReplayCompleteRequest(
                sir_convert_job_id=sir_convert_job_id,
                correlation_id="corr-replay-1",
                status="succeeded",
                requested_artifacts=["txt", "md", "vtt", "srt"],
                result=result_payload,
                artifact_payloads=_four_artifact_payloads(
                    receipt_authority=receipt_authority,
                    job_id=sir_convert_job_id,
                ),
            ),
        )

    assert exc.value.code is ErrorCode.SERVICE_UNAVAILABLE
    assert artifacts.records == {}


def _result_body(payload: dict[str, object]) -> dict[str, object]:
    body = payload["result"]
    assert isinstance(body, dict)
    return body


def _result_artifact(payload: dict[str, object]) -> dict[str, object]:
    artifact = _result_body(payload)["artifact"]
    assert isinstance(artifact, dict)
    return artifact


def _result_metadata(payload: dict[str, object]) -> dict[str, object]:
    metadata = _result_body(payload)["conversion_metadata"]
    assert isinstance(metadata, dict)
    return metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_accepts_service_v2_result_envelope_and_four_artifacts() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    sir_convert_job_id = "jobv2_replay_success"
    artifact_ids = [uuid4(), uuid4(), uuid4(), uuid4()]
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    artifacts = replay_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(now=replay_fixtures._now())
    handler = transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=InMemoryConversionHubJobRepository(),
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(replay_fixtures._now()),
        id_generator=SequentialIdGenerator([local_job_id, *artifact_ids]),
    )

    result = await handler.handle(
        actor=actor,
        authenticated_huleedu_subject="teacher-subject-1",
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterReplayCompleteRequest(
            sir_convert_job_id=sir_convert_job_id,
            correlation_id="corr-replay-1",
            status="succeeded",
            requested_artifacts=["txt", "md", "vtt", "srt"],
            result=_service_result_envelope(job_id=sir_convert_job_id),
            artifact_payloads=_four_artifact_payloads(
                receipt_authority=receipt_authority,
                job_id=sir_convert_job_id,
            ),
        ),
    )

    assert result.conversion_hub_job_id == local_job_id
    assert [artifact.artifact_key for artifact in result.artifacts] == [
        "transcript_txt",
        "transcript_md",
        "transcript_vtt",
        "transcript_srt",
    ]
    assert {artifact.artifact_key: artifact.retrieval_path for artifact in result.artifacts} == {
        key.value: f"/v2/convert/jobs/{sir_convert_job_id}/artifacts/{key.value}"
        for key in ConversionHubTranscriptFormatterArtifactKey
    }
    assert sorted(record.id for record in artifacts.records.values()) == sorted(artifact_ids)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_result_envelope_for_different_job_id() -> None:
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
        id_generator=SequentialIdGenerator([uuid4(), uuid4(), uuid4(), uuid4(), uuid4()]),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-1",
            transcript_id=transcript_id,
            request=ConversionHubTranscriptFormatterReplayCompleteRequest(
                sir_convert_job_id="jobv2_replay_success",
                correlation_id="corr-replay-1",
                status="succeeded",
                requested_artifacts=["txt", "md", "vtt", "srt"],
                result=_service_result_envelope(job_id="jobv2_other"),
                artifact_payloads=_four_artifact_payloads(
                    receipt_authority=receipt_authority,
                    job_id="jobv2_replay_success",
                ),
            ),
        )

    assert exc.value.code is ErrorCode.SERVICE_UNAVAILABLE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_result_without_warnings_list() -> None:
    missing_warnings = _service_result_envelope(job_id="jobv2_replay_success")
    _result_body(missing_warnings).pop("warnings")
    string_warnings = _service_result_envelope(job_id="jobv2_replay_success")
    _result_body(string_warnings)["warnings"] = "producer-warning"

    for result_payload in (missing_warnings, string_warnings):
        await _assert_completion_rejects_result(result_payload=result_payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_wrong_result_status() -> None:
    result_payload = _service_result_envelope(job_id="jobv2_replay_success")
    result_payload["status"] = "failed"

    await _assert_completion_rejects_result(result_payload=result_payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_malformed_result_artifact_metadata() -> None:
    missing_sha = _service_result_envelope(job_id="jobv2_replay_success")
    _result_artifact(missing_sha).pop("sha256")
    wrong_content_type = _service_result_envelope(job_id="jobv2_replay_success")
    _result_artifact(wrong_content_type)["content_type"] = "text/plain"

    malformed_results: Sequence[dict[str, object]] = (missing_sha, wrong_content_type)
    for result_payload in malformed_results:
        await _assert_completion_rejects_result(result_payload=result_payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_replay_rejects_malformed_conversion_metadata() -> None:
    wrong_pipeline = _service_result_envelope(job_id="jobv2_replay_success")
    _result_metadata(wrong_pipeline)["pipeline_used"] = "audio_to_transcript_bundle_v2"
    runtime_provider = _service_result_envelope(job_id="jobv2_replay_success")
    _result_metadata(runtime_provider)["backend_used"] = "whisper"
    formula_authority = _service_result_envelope(job_id="jobv2_replay_success")
    _result_metadata(formula_authority)["formula_authority"] = {"route": "unexpected"}

    malformed_results: Sequence[dict[str, object]] = (
        wrong_pipeline,
        runtime_provider,
        formula_authority,
    )
    for result_payload in malformed_results:
        await _assert_completion_rejects_result(result_payload=result_payload)
