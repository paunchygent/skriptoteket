"""Unit tests for public Exam Converter upstream client adapters.

Purpose:
  Prove Skriptoteket's public Exam Converter infrastructure clients keep
  HuleEdu grant minting and Sir Convert artifact-read leasing as separate
  server-side authorities.

Relationships:
  - Exercises the HuleEdu grant-only client request/response shape.
  - Exercises the Sir Convert public grant/read-lease client header contract.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import httpx
import pytest

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterTarget,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    public_exam_converter_grants,
    public_exam_converter_sir_convert_client_v2,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertClientSettingsV2,
)
from skriptoteket.protocols.public_exam_converter import (
    PublicExamConverterGrantRequest,
    PublicExamConverterSirConvertSubmitRequest,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_huleedu_grant_client_sends_grant_only_request_with_signed_assertion() -> None:
    captured_payload: dict[str, object] = {}
    captured_correlation_id: str | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload, captured_correlation_id
        captured_correlation_id = request.headers.get("X-Correlation-ID")
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "public_conversion_grant": "opaque-public-grant",
                "artifact_ttl_seconds": 3600,
                "expires_at": "2026-05-13T20:00:00+00:00",
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://huleedu.example") as client:
        authority = public_exam_converter_grants.HuleEduPublicExamConverterGrantAuthority(
            settings=public_exam_converter_grants.PublicExamConverterGrantAuthoritySettings(
                base_url="https://huleedu.example",
                client_id="skriptoteket-backend",
                client_assertion="",
                client_assertion_secret="assertion-secret",
                assertion_audience="huleedu-public-grant",
                timeout_seconds=5.0,
                fallback_artifact_ttl_seconds=1800,
            ),
            client=client,
        )
        grant = await authority.mint_conversion_grant(
            request=PublicExamConverterGrantRequest(
                upload_digest="sha256:abc123",
                aggregate_upload_bytes=123,
                upload_mime_types=("application/octet-stream", "application/pdf"),
                allowed_targets=(PublicExamConverterTarget.EXAMNET_PDF,),
                correlation_id="corr-public",
            )
        )

    assert captured_correlation_id == "corr-public"
    assert captured_payload["client_id"] == "skriptoteket-backend"
    assert captured_payload["assertion_aud"] == "huleedu-public-grant"
    assert captured_payload["allowed_targets"] == ["examnet_pdf"]
    assert captured_payload["upload_mime_types"] == [
        "application/octet-stream",
        "application/pdf",
    ]
    assert "public_artifact_read_lease" not in captured_payload
    assert "artifact_read_lease" not in captured_payload

    assertion = captured_payload["client_assertion"]
    assert isinstance(assertion, str)
    assertion_payload = _decode_jwt_payload(assertion)
    assert assertion_payload["iss"] == "skriptoteket-backend"
    assert assertion_payload["sub"] == "skriptoteket-backend"
    assert assertion_payload["aud"] == "huleedu-public-grant"
    assert isinstance(assertion_payload["jti"], str)

    assert grant.token == "opaque-public-grant"
    assert grant.artifact_ttl_seconds == 3600
    assert grant.expires_at == datetime(2026, 5, 13, 20, 0, tzinfo=UTC)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_sir_convert_client_uses_parent_grant_and_exact_artifact_leases() -> None:
    captured: list[tuple[str, str, dict[str, str]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path, dict(request.headers)))
        if request.method == "POST":
            return httpx.Response(
                200,
                headers={"X-Idempotent-Replay": "true"},
                json={
                    "job": {"job_id": "job-1", "status": "succeeded"},
                    "public_artifact_read_lease": {"token": "manifest-lease"},
                },
            )
        if request.url.path == "/v2/convert/jobs/job-1":
            return httpx.Response(200, json={"job": {"job_id": "job-1", "status": "succeeded"}})
        if request.url.path == "/v2/convert/jobs/job-1/result":
            return httpx.Response(200, json={"job_id": "job-1", "status": "succeeded"})
        if request.url.path == "/v2/convert/jobs/job-1/artifacts":
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {
                            "artifact_key": "examnet_pdf",
                            "public_artifact_read_lease": {"token": "artifact-lease"},
                        }
                    ]
                },
            )
        if request.url.path == "/v2/convert/jobs/job-1/artifacts/examnet_pdf":
            return httpx.Response(
                200,
                content=b"%PDF-1.7",
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Disposition": 'attachment; filename="examnet.pdf"',
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        svc = public_exam_converter_sir_convert_client_v2.PublicExamConverterSirConvertClientV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="sir-convert-key",
                timeout_seconds=10.0,
            ),
            client=client,
        )
        submitted = await svc.submit_public_exam_converter_job(
            request=PublicExamConverterSirConvertSubmitRequest(
                filename="exam.dxe",
                content_type="application/octet-stream",
                file_bytes=b"DXE",
                job_spec={"api_version": "v2"},
                idempotency_key="idem-public",
                wait_seconds=0,
                correlation_id="corr-public",
                public_conversion_grant="opaque-public-grant",
            )
        )
        job = await svc.get_public_exam_converter_job(
            "job-1",
            public_conversion_grant="opaque-public-grant",
            correlation_id="corr-public",
        )
        result = await svc.get_public_exam_converter_result(
            "job-1",
            public_conversion_grant="opaque-public-grant",
            correlation_id="corr-public",
        )
        manifest = await svc.get_public_exam_converter_artifact_manifest(
            "job-1",
            public_conversion_grant="opaque-public-grant",
            public_artifact_read_lease="manifest-lease",
            correlation_id="corr-public",
        )
        artifact = await svc.download_public_exam_converter_artifact(
            "job-1",
            artifact_key="examnet_pdf",
            public_conversion_grant="opaque-public-grant",
            public_artifact_read_lease="artifact-lease",
            correlation_id="corr-public",
        )

    assert submitted.manifest_artifact_read_lease_token == "manifest-lease"
    assert submitted.idempotent_replay is True
    assert job.status == "succeeded"
    assert result["status"] == "succeeded"
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    first_artifact = artifacts[0]
    assert isinstance(first_artifact, dict)
    assert first_artifact["artifact_key"] == "examnet_pdf"
    assert artifact.filename == "examnet.pdf"
    assert artifact.content == b"%PDF-1.7"

    expected_paths = [
        ("POST", "/v2/convert/jobs"),
        ("GET", "/v2/convert/jobs/job-1"),
        ("GET", "/v2/convert/jobs/job-1/result"),
        ("GET", "/v2/convert/jobs/job-1/artifacts"),
        ("GET", "/v2/convert/jobs/job-1/artifacts/examnet_pdf"),
    ]
    assert [(method, path) for method, path, _ in captured] == expected_paths
    for _, _, headers in captured:
        assert headers["x-api-key"] == "sir-convert-key"
        assert headers["x-correlation-id"] == "corr-public"
        assert headers["x-public-conversion-grant"] == "opaque-public-grant"
    assert "x-public-artifact-read-lease" not in captured[0][2]
    assert "x-public-artifact-read-lease" not in captured[1][2]
    assert "x-public-artifact-read-lease" not in captured[2][2]
    assert captured[3][2]["x-public-artifact-read-lease"] == "manifest-lease"
    assert captured[4][2]["x-public-artifact-read-lease"] == "artifact-lease"


def _decode_jwt_payload(token: str) -> dict[str, object]:
    _, payload_segment, _ = token.split(".", maxsplit=2)
    padding = "=" * (-len(payload_segment) % 4)
    decoded = base64.urlsafe_b64decode(f"{payload_segment}{padding}".encode("ascii"))
    payload = json.loads(decoded)
    assert isinstance(payload, dict)
    return payload
