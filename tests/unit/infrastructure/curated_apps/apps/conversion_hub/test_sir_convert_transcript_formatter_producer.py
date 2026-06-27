"""Tests for the Sir Convert transcript formatter producer client.

Domain purpose:
  Prove Skriptoteket's backend producer client can consume Sir Convert's
  transcript-json formatter job lifecycle without leaking orchestration to the
  browser.

Relationships:
  - Exercises `SirConvertTranscriptFormatterProducerV2`.
  - Complements application export-handler tests by covering real HTTP status
    and polling behavior at the infrastructure boundary.
"""

from __future__ import annotations

import httpx
import pytest

from skriptoteket.application.curated_apps.conversion_hub_transcript_formatter_contracts import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    sir_convert_transcript_formatter_producer as producer_module,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertClientSettingsV2,
)
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterProducerRequest,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertJobStatusV2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_formatter_producer_polls_accepted_async_job_to_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests_seen: list[tuple[str, str]] = []
    status_payloads = iter(["running", "succeeded"])
    artifact_payloads = {
        "transcript_txt": b"Anna: Hello.\n",
        "transcript_md": b"## Transcript\n\nAnna: Hello.\n",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            return httpx.Response(
                202,
                json={"job": {"job_id": "job-async-1", "status": "queued"}},
            )
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job-async-1":
            return httpx.Response(
                200,
                json={"job": {"job_id": "job-async-1", "status": next(status_payloads)}},
            )
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job-async-1/result":
            return httpx.Response(
                200,
                json={"artifact_key": "transcript_replay_bundle_manifest"},
            )
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job-async-1/artifacts":
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {"artifact_key": "transcript_txt"},
                        {"artifact_key": "transcript_md"},
                    ]
                },
            )
        if request.method == "GET" and request.url.path.startswith(
            "/v2/convert/jobs/job-async-1/artifacts/"
        ):
            artifact_key = request.url.path.rsplit("/", maxsplit=1)[-1]
            return httpx.Response(
                200,
                content=artifact_payloads[artifact_key],
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(
        producer_module,
        "_FORMATTER_EXPORT_POLL_INTERVAL_SECONDS",
        0.0,
        raising=False,
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        producer = producer_module.SirConvertTranscriptFormatterProducerV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="test-key",
                timeout_seconds=10.0,
            ),
            client=client,
        )
        result = await producer.create_transcript_formatter_export(
            request=ConversionHubTranscriptFormatterProducerRequest(
                filename="saved-transcript.json",
                content_type="application/json",
                file_bytes=b'{"schema_version":"transcript_json_v1"}',
                job_spec={
                    "api_version": "v2",
                    "source": {
                        "kind": "upload",
                        "filename": "saved-transcript.json",
                        "format": "transcript_json",
                    },
                    "conversion": {"output_format": "transcript_bundle"},
                    "transcript_formatter_options": {
                        "schema_version": "transcript_formatter_replay_v1",
                        "requested_artifacts": ["txt", "md"],
                        "speaker_label_overrides": [],
                    },
                    "retention": {"pin": False},
                },
                requested_artifacts=(
                    ConversionHubTranscriptFormatterArtifactFormat.TXT,
                    ConversionHubTranscriptFormatterArtifactFormat.MD,
                ),
                idempotency_key="idem-export-1",
                correlation_id="corr-export-1",
                wait_seconds=0,
            )
        )

    assert result.sir_convert_job_id == "job-async-1"
    assert result.status is SirConvertJobStatusV2.SUCCEEDED
    assert result.result == {"artifact_key": "transcript_replay_bundle_manifest"}
    assert result.artifact_manifest == {
        "artifacts": [
            {"artifact_key": "transcript_txt"},
            {"artifact_key": "transcript_md"},
        ]
    }
    assert (
        result.artifacts[ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT].content
        == artifact_payloads["transcript_txt"]
    )
    assert (
        result.artifacts[ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD].content
        == artifact_payloads["transcript_md"]
    )
    assert requests_seen == [
        ("POST", "/v2/convert/jobs"),
        ("GET", "/v2/convert/jobs/job-async-1"),
        ("GET", "/v2/convert/jobs/job-async-1"),
        ("GET", "/v2/convert/jobs/job-async-1/result"),
        ("GET", "/v2/convert/jobs/job-async-1/artifacts"),
        ("GET", "/v2/convert/jobs/job-async-1/artifacts/transcript_txt"),
        ("GET", "/v2/convert/jobs/job-async-1/artifacts/transcript_md"),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_formatter_producer_recovers_stale_idempotent_queued_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests_seen: list[tuple[str, str, str | None]] = []
    artifact_payloads = {
        "transcript_txt": b"Anna: Hello.\n",
        "transcript_md": b"## Transcript\n\nAnna: Hello.\n",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        idempotency_key = request.headers.get("Idempotency-Key")
        requests_seen.append((request.method, request.url.path, idempotency_key))
        if request.method == "POST" and idempotency_key == "idem-export-1":
            return httpx.Response(
                202,
                json={
                    "job": {
                        "job_id": "job-stale-1",
                        "status": "queued",
                        "updated_at": "2000-01-01T00:00:00Z",
                    }
                },
            )
        if (
            request.method == "POST"
            and idempotency_key is not None
            and idempotency_key.startswith("idem-export-1:recover:job-stale-1:")
        ):
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "job-recovered-1",
                        "status": "succeeded",
                        "updated_at": "2026-06-14T19:43:03Z",
                    }
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v2/convert/jobs/job-recovered-1/result"
        ):
            return httpx.Response(
                200,
                json={"artifact_key": "transcript_replay_bundle_manifest"},
            )
        if (
            request.method == "GET"
            and request.url.path == "/v2/convert/jobs/job-recovered-1/artifacts"
        ):
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {"artifact_key": "transcript_txt"},
                        {"artifact_key": "transcript_md"},
                    ]
                },
            )
        if request.method == "GET" and request.url.path.startswith(
            "/v2/convert/jobs/job-recovered-1/artifacts/"
        ):
            artifact_key = request.url.path.rsplit("/", maxsplit=1)[-1]
            return httpx.Response(
                200,
                content=artifact_payloads[artifact_key],
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    monkeypatch.setattr(
        producer_module,
        "_FORMATTER_EXPORT_POLL_INTERVAL_SECONDS",
        0.0,
        raising=False,
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        producer = producer_module.SirConvertTranscriptFormatterProducerV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="test-key",
                timeout_seconds=10.0,
            ),
            client=client,
        )
        result = await producer.create_transcript_formatter_export(
            request=ConversionHubTranscriptFormatterProducerRequest(
                filename="saved-transcript.json",
                content_type="application/json",
                file_bytes=b'{"schema_version":"transcript_json_v1"}',
                job_spec={
                    "api_version": "v2",
                    "source": {
                        "kind": "upload",
                        "filename": "saved-transcript.json",
                        "format": "transcript_json",
                    },
                    "conversion": {"output_format": "transcript_bundle"},
                    "transcript_formatter_options": {
                        "schema_version": "transcript_formatter_replay_v1",
                        "requested_artifacts": ["txt", "md"],
                        "speaker_label_overrides": [],
                    },
                    "retention": {"pin": False},
                },
                requested_artifacts=(
                    ConversionHubTranscriptFormatterArtifactFormat.TXT,
                    ConversionHubTranscriptFormatterArtifactFormat.MD,
                ),
                idempotency_key="idem-export-1",
                correlation_id="corr-export-1",
                wait_seconds=0,
            )
        )

    assert result.sir_convert_job_id == "job-recovered-1"
    assert result.status is SirConvertJobStatusV2.SUCCEEDED
    assert (
        result.artifacts[ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT].content
        == artifact_payloads["transcript_txt"]
    )
    assert requests_seen[0] == ("POST", "/v2/convert/jobs", "idem-export-1")
    assert requests_seen[1][0:2] == ("POST", "/v2/convert/jobs")
    assert requests_seen[1][2] is not None
    assert requests_seen[1][2].startswith("idem-export-1:recover:job-stale-1:")
    assert all("job-stale-1" not in path for _, path, _ in requests_seen[2:])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_formatter_producer_rejects_unknown_upstream_status_fail_closed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            return httpx.Response(
                202,
                json={"job": {"job_id": "job-unknown", "status": "paused"}},
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        producer = producer_module.SirConvertTranscriptFormatterProducerV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="test-key",
                timeout_seconds=10.0,
            ),
            client=client,
        )
        with pytest.raises(DomainError) as excinfo:
            await producer.create_transcript_formatter_export(
                request=ConversionHubTranscriptFormatterProducerRequest(
                    filename="saved-transcript.json",
                    content_type="application/json",
                    file_bytes=b'{"schema_version":"transcript_json_v1"}',
                    job_spec={
                        "api_version": "v2",
                        "source": {
                            "kind": "upload",
                            "filename": "saved-transcript.json",
                            "format": "transcript_json",
                        },
                        "conversion": {"output_format": "transcript_bundle"},
                        "transcript_formatter_options": {
                            "schema_version": "transcript_formatter_replay_v1",
                            "requested_artifacts": ["txt"],
                            "speaker_label_overrides": [],
                        },
                        "retention": {"pin": False},
                    },
                    requested_artifacts=(ConversionHubTranscriptFormatterArtifactFormat.TXT,),
                    idempotency_key="idem-export-unknown",
                    correlation_id="corr-export-unknown",
                    wait_seconds=0,
                )
            )

    assert excinfo.value.code is ErrorCode.SERVICE_UNAVAILABLE
    assert excinfo.value.details == {
        "reason_code": "sir_convert_unknown_job_status",
        "status": "paused",
    }
