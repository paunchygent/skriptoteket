"""Unit coverage for Conversion Hub saved transcript API routes.

Domain purpose:
  Prove PR-0343 route functions expose durable transcript save/readback
  contracts while preserving the app-access boundary.

Relationships:
  - Covers `web.api.v1.apps_conversion_hub_transcript_saves`.
  - Complements handler tests for owner-scope and validation.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Generic, TypeVar
from uuid import UUID, uuid4

import pytest
from fastapi import Response

from skriptoteket.application.curated_apps.conversion_hub import (
    RegisterTranscriptConversionHubJobRequest,
    RegisterTranscriptConversionHubJobResult,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactDownload,
    SaveConversionHubTranscriptFormatterArtifactResult,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterReplayCompleteRequest,
    ConversionHubTranscriptFormatterReplayPrepareRequest,
    ConversionHubTranscriptFormatterReplayPrepareResponse,
    ConversionHubTranscriptFormatterReplayResponse,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscriptResponse,
    ConversionHubTranscriptSpeakerOverlaysResponse,
    SaveConversionHubTranscriptRequest,
    UpdateConversionHubTranscriptSpeakerOverlaysRequest,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_conversion_hub_transcript_saves as api
from tests.fixtures.identity_fixtures import make_user

RouteCallable = Callable[..., Awaitable[object]]
ResultT = TypeVar("ResultT", bound=object)


def _unwrap_dishka(fn: RouteCallable) -> RouteCallable:
    return getattr(fn, "__dishka_orig_func__", fn)


class FakeRegistry:
    def get_by_app_id(self, *, app_id: str):
        return SimpleNamespace(app_id=app_id, min_role=Role.USER)


class CapturingHandler(Generic[ResultT]):
    def __init__(self, result: ResultT) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs: object) -> ResultT:
        self.calls.append(kwargs)
        return self.result


def _request() -> SaveConversionHubTranscriptRequest:
    return SaveConversionHubTranscriptRequest(
        sir_convert_job_id="sir-transcript-job-1",
        artifact_key="transcript_json",
        source_filename="seminarium.m4a",
        transcript_json={
            "schema_version": "transcript_json_v1",
            "transcript": {
                "text": "Hej.",
                "segments": [
                    {
                        "id": "seg_1",
                        "start_seconds": 0,
                        "end_seconds": 2,
                        "speaker_label": "SPEAKER_00",
                        "text": "Hej.",
                    }
                ],
            },
        },
        transcript_schema_version="transcript_json_v1",
        language_code="sv",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-transcript-1",
    )


def _response() -> ConversionHubSavedTranscriptResponse:
    return ConversionHubSavedTranscriptResponse(
        transcript_id=uuid4(),
        owner_user_id=uuid4(),
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
        generated_at=datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-transcript-1",
        transcript_json=_request().transcript_json,
        created_at=datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc),
    )


def _speaker_overlays_request() -> UpdateConversionHubTranscriptSpeakerOverlaysRequest:
    return UpdateConversionHubTranscriptSpeakerOverlaysRequest(
        overlays=[
            {
                "canonical_speaker_label": "SPEAKER_00",
                "display_name": "Anna Andersson",
            }
        ]
    )


def _speaker_overlays_response(
    transcript_id: UUID,
) -> ConversionHubTranscriptSpeakerOverlaysResponse:
    return ConversionHubTranscriptSpeakerOverlaysResponse(
        transcript_id=transcript_id,
        overlays=[
            {
                "canonical_speaker_label": "SPEAKER_00",
                "display_name": "Anna Andersson",
            }
        ],
        updated_at=datetime(2026, 6, 12, 11, 0, tzinfo=timezone.utc),
    )


def _register_request() -> RegisterTranscriptConversionHubJobRequest:
    return RegisterTranscriptConversionHubJobRequest(
        upstream_job_id="sir-transcript-job-1",
        input_filename="seminarium.m4a",
        correlation_id="corr-transcript-1",
    )


def _register_response() -> RegisterTranscriptConversionHubJobResult:
    return RegisterTranscriptConversionHubJobResult(
        job_id=uuid4(),
        upstream_job_id="sir-transcript-job-1",
        status="succeeded",
    )


def _replay_prepare_response(
    transcript_id: UUID,
) -> ConversionHubTranscriptFormatterReplayPrepareResponse:
    return ConversionHubTranscriptFormatterReplayPrepareResponse(
        transcript_id=transcript_id,
        correlation_id="corr-replay-1",
        idempotency_key="idem-replay-1",
        gateway_filename=f"saved-transcript-{transcript_id}.json",
        transcript_json={"schema_version": "transcript_json_v1"},
        job_spec={
            "api_version": "v2",
            "source": {
                "kind": "upload",
                "filename": f"saved-transcript-{transcript_id}.json",
                "format": "transcript_json",
            },
            "conversion": {"output_format": "transcript_bundle"},
            "transcript_formatter_options": {
                "schema_version": "transcript_formatter_replay_v1",
                "requested_artifacts": ["txt"],
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"}
                ],
            },
            "retention": {"pin": False},
        },
    )


def _replay_complete_request() -> ConversionHubTranscriptFormatterReplayCompleteRequest:
    return ConversionHubTranscriptFormatterReplayCompleteRequest(
        sir_convert_job_id="sir-replay-job-1",
        correlation_id="corr-replay-1",
        status="succeeded",
        requested_artifacts=["txt"],
        result={
            "result": {
                "artifact": {
                    "filename": "transcript_replay_bundle_manifest.json",
                    "format": "transcript_bundle",
                    "content_type": "application/json",
                    "size_bytes": 32,
                    "sha256": "abc",
                },
                "conversion_metadata": {
                    "pipeline_used": "transcript_json_to_transcript_bundle_replay_v2",
                    "options_fingerprint": "sha256:abc",
                },
            }
        },
        artifact_manifest={"api_version": "v2", "job_id": "sir-replay-job-1", "artifacts": []},
    )


def _replay_response(transcript_id: UUID) -> ConversionHubTranscriptFormatterReplayResponse:
    return ConversionHubTranscriptFormatterReplayResponse(
        transcript_id=transcript_id,
        conversion_hub_job_id=uuid4(),
        sir_convert_job_id="sir-replay-job-1",
        correlation_id="corr-replay-1",
        requested_artifacts=["txt"],
        artifacts=[
            {
                "requested_artifact": "txt",
                "artifact_key": "transcript_txt",
                "filename": "transcript_txt.txt",
                "content_type": "text/plain",
                "size_bytes": 12,
                "sha256": "abc",
                "retrieval_path": "/v2/convert/jobs/sir-replay-job-1/artifacts/transcript_txt",
            }
        ],
    )


def _formatter_artifact_download() -> ConversionHubTranscriptFormatterArtifactDownload:
    return ConversionHubTranscriptFormatterArtifactDownload(
        filename="transkript-abcdef12.txt",
        content_type="text/plain",
        content=b"overlay-aware transcript\n",
    )


def _formatter_artifact_save_response() -> SaveConversionHubTranscriptFormatterArtifactResult:
    return SaveConversionHubTranscriptFormatterArtifactResult(
        source_artifact_id="documents.conversion_hub:transcript-replay:local-job:transcript_txt",
        vault_artifact=ConversionHubSavedVaultArtifact(
            file_id=uuid4(),
            name="transkript-abcdef12.txt",
            bytes=25,
            created_at=datetime(2026, 6, 13, 12, 5, tzinfo=timezone.utc),
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_transcript_delegates_to_handler() -> None:
    user = make_user()
    job_id = uuid4()
    request = _request()
    handler = CapturingHandler(_response())

    result = await _unwrap_dishka(api.save_conversion_hub_transcript)(
        job_id=job_id,
        request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, ConversionHubSavedTranscriptResponse)
    assert result.sir_convert_job_id == "sir-transcript-job-1"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["conversion_hub_job_id"] == job_id
    assert handler.calls[0]["request"] == request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_transcript_job_delegates_to_handler() -> None:
    user = make_user()
    request = _register_request()
    handler = CapturingHandler(_register_response())

    result = await _unwrap_dishka(api.register_transcript_job)(
        register_request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, RegisterTranscriptConversionHubJobResult)
    assert result.upstream_job_id == "sir-transcript-job-1"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["request"] == request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_saved_transcript_delegates_to_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    handler = CapturingHandler(_response())

    result = await _unwrap_dishka(api.get_conversion_hub_transcript)(
        transcript_id=transcript_id,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, ConversionHubSavedTranscriptResponse)
    assert result.transcript_schema_version == "transcript_json_v1"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_speaker_overlays_delegates_to_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    handler = CapturingHandler(_speaker_overlays_response(transcript_id))

    result = await _unwrap_dishka(api.list_conversion_hub_transcript_speaker_overlays)(
        transcript_id=transcript_id,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, ConversionHubTranscriptSpeakerOverlaysResponse)
    assert result.overlays[0].display_name == "Anna Andersson"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_speaker_overlays_delegates_to_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    request = _speaker_overlays_request()
    handler = CapturingHandler(_speaker_overlays_response(transcript_id))

    result = await _unwrap_dishka(api.update_conversion_hub_transcript_speaker_overlays)(
        transcript_id=transcript_id,
        request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, ConversionHubTranscriptSpeakerOverlaysResponse)
    assert result.transcript_id == transcript_id
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id
    assert handler.calls[0]["request"] == request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_formatter_replay_delegates_to_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    request = ConversionHubTranscriptFormatterReplayPrepareRequest(requested_artifacts=["txt"])
    handler = CapturingHandler(_replay_prepare_response(transcript_id))

    result = await _unwrap_dishka(api.prepare_conversion_hub_transcript_formatter_replay)(
        transcript_id=transcript_id,
        replay_request=request,
        request=SimpleNamespace(state=SimpleNamespace(correlation_id=None)),
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, ConversionHubTranscriptFormatterReplayPrepareResponse)
    assert result.job_spec.source.format == "transcript_json"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id
    assert handler.calls[0]["request"] == request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_formatter_replay_delegates_to_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    request = _replay_complete_request()
    handler = CapturingHandler(_replay_response(transcript_id))

    result = await _unwrap_dishka(api.complete_conversion_hub_transcript_formatter_replay)(
        transcript_id=transcript_id,
        replay_request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, ConversionHubTranscriptFormatterReplayResponse)
    assert result.artifacts[0].artifact_key == "transcript_txt"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id
    assert handler.calls[0]["request"] == request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_formatter_artifact_delegates_to_owner_scoped_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    correlation_id = uuid4()
    handler = CapturingHandler(_formatter_artifact_download())

    response = await _unwrap_dishka(api.download_conversion_hub_transcript_formatter_artifact)(
        transcript_id=transcript_id,
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        request=SimpleNamespace(state=SimpleNamespace(correlation_id=correlation_id)),
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.body == b"overlay-aware transcript\n"
    assert response.media_type == "text/plain"
    assert response.headers["Cache-Control"] == "no-store"
    assert 'filename="transkript-abcdef12.txt"' in response.headers["Content-Disposition"]
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id
    assert handler.calls[0]["artifact_key"] is (
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT
    )
    assert handler.calls[0]["correlation_id"] == str(correlation_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_formatter_artifact_delegates_to_owner_scoped_handler() -> None:
    user = make_user()
    transcript_id = uuid4()
    correlation_id = uuid4()
    handler = CapturingHandler(_formatter_artifact_save_response())

    result = await _unwrap_dishka(api.save_conversion_hub_transcript_formatter_artifact)(
        transcript_id=transcript_id,
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        request=SimpleNamespace(state=SimpleNamespace(correlation_id=correlation_id)),
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert isinstance(result, SaveConversionHubTranscriptFormatterArtifactResult)
    assert result.vault_artifact.name == "transkript-abcdef12.txt"
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["transcript_id"] == transcript_id
    assert handler.calls[0]["artifact_key"] is (
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT
    )
    assert handler.calls[0]["correlation_id"] == str(correlation_id)
