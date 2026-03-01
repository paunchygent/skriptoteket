"""Unit tests for the async Sir Convert-a-Lot v2 client wrapper.

These tests validate request shaping + error mapping for the Conversion Hub integration seam.
"""

from __future__ import annotations

import io

import httpx
import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertALotClientV2,
    SirConvertClientSettingsV2,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_job_sends_api_key_and_idempotency_key_and_job_spec_payload() -> None:
    captured_headers: dict[str, str] = {}
    captured_url: str | None = None
    captured_body: str | None = None
    captured_api_key: str | None = None
    captured_idempotency_key: str | None = None
    captured_correlation_id: str | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers, captured_url, captured_body
        nonlocal captured_api_key, captured_idempotency_key, captured_correlation_id
        captured_headers = dict(request.headers)
        captured_url = str(request.url)
        captured_body = request.content.decode("utf-8", errors="replace")
        captured_api_key = request.headers.get("X-API-Key")
        captured_idempotency_key = request.headers.get("Idempotency-Key")
        captured_correlation_id = request.headers.get("X-Correlation-ID")

        return httpx.Response(
            202,
            headers={"X-Idempotent-Replay": "true"},
            json={"job": {"job_id": "job-1", "status": "queued"}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        svc = SirConvertALotClientV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="test-key",
                timeout_seconds=10.0,
            ),
            client=client,
        )
        submitted = await svc.submit_job(
            filename="input.html",
            content_type="text/html",
            file_handle=io.BytesIO(b"<html></html>"),
            job_spec={"api_version": "v2", "source": {"kind": "upload"}, "conversion": {}},
            idempotency_key="idem-1",
            wait_seconds=0,
            correlation_id="corr-1",
        )

    assert captured_url is not None
    assert captured_url.endswith("/v2/convert/jobs?wait_seconds=0")
    assert captured_api_key == "test-key"
    assert captured_idempotency_key == "idem-1"
    assert captured_correlation_id == "corr-1"

    assert submitted.job_id == "job-1"
    assert submitted.status == "queued"
    assert submitted.idempotent_replay is True

    assert captured_body is not None
    assert "job_spec" in captured_body
    # Best-effort: the body should contain our JSON spec string.
    assert '"api_version":"v2"' in captured_body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_job_maps_upstream_error_to_domain_error_with_details() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": {"code": "service_unavailable", "message": "down", "retryable": True}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        svc = SirConvertALotClientV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="test-key",
                timeout_seconds=10.0,
            ),
            client=client,
        )
        with pytest.raises(DomainError) as excinfo:
            await svc.submit_job(
                filename="input.html",
                content_type="text/html",
                file_handle=io.BytesIO(b"<html></html>"),
                job_spec={"api_version": "v2", "source": {"kind": "upload"}, "conversion": {}},
                idempotency_key="idem-1",
                wait_seconds=0,
                correlation_id=None,
            )

    assert excinfo.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert excinfo.value.details.get("upstream_status_code") == 503
    assert excinfo.value.details.get("upstream_code") == "service_unavailable"
    assert excinfo.value.details.get("upstream_retryable") is True
