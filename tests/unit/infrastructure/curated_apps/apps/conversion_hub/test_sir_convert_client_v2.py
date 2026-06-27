"""Unit tests for the async Sir Convert-a-Lot v2 client wrapper.

These tests validate request shaping + error mapping for the Conversion Hub integration seam.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    sir_convert_client_v2 as sir_convert_client_v2_module,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertALotClientV2,
    SirConvertClientSettingsV2,
    build_sir_convert_async_http_client,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertJobStatusV2,
    SirConvertSubmitRequestV2,
    parse_sir_convert_job_status_v2,
)

CONTRACT_FIXTURE = (
    Path(__file__).resolve().parents[5]
    / "fixtures"
    / "sir_convert_a_lot_v2_job_status_contract.json"
)


def _contract_status_values() -> set[str]:
    payload = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
    values = payload["components"]["schemas"]["SirConvertJobStatusV2"]["enum"]
    return set(values)


@pytest.mark.unit
def test_sir_convert_job_status_enum_matches_committed_v2_contract_fixture() -> None:
    assert {status.value for status in SirConvertJobStatusV2} == _contract_status_values()


@pytest.mark.unit
def test_sir_convert_job_status_parser_rejects_unknown_status_fail_closed() -> None:
    with pytest.raises(DomainError) as excinfo:
        parse_sir_convert_job_status_v2("paused")

    assert excinfo.value.code is ErrorCode.SERVICE_UNAVAILABLE
    assert excinfo.value.details == {
        "reason_code": "sir_convert_unknown_job_status",
        "status": "paused",
    }


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
            request=SirConvertSubmitRequestV2(
                filename="input.html",
                content_type="text/html",
                file_bytes=b"<html></html>",
                job_spec={"api_version": "v2", "source": {"kind": "upload"}, "conversion": {}},
                idempotency_key="idem-1",
                wait_seconds=0,
                correlation_id="corr-1",
                resources_filename="resources.zip",
                resources_bytes=b"PK",
            )
        )

    assert captured_url is not None
    assert captured_url.endswith("/v2/convert/jobs?wait_seconds=0")
    assert captured_api_key == "test-key"
    assert captured_idempotency_key == "idem-1"
    assert captured_correlation_id == "corr-1"

    assert submitted.job_id == "job-1"
    assert submitted.status is SirConvertJobStatusV2.QUEUED
    assert submitted.idempotent_replay is True

    assert captured_body is not None
    assert "job_spec" in captured_body
    assert "resources.zip" in captured_body
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
                request=SirConvertSubmitRequestV2(
                    filename="input.html",
                    content_type="text/html",
                    file_bytes=b"<html></html>",
                    job_spec={"api_version": "v2", "source": {"kind": "upload"}, "conversion": {}},
                    idempotency_key="idem-1",
                    wait_seconds=0,
                    correlation_id=None,
                )
            )

    assert excinfo.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert excinfo.value.details.get("upstream_status_code") == 503
    assert excinfo.value.details.get("upstream_code") == "service_unavailable"
    assert excinfo.value.details.get("upstream_retryable") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_text_direct_submits_pdf_to_markdown_job_and_decodes_artifact() -> None:
    captured_body: str | None = None
    captured_correlation_ids: list[str | None] = []
    captured_requests: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_requests.append((request.method, request.url.path))
        captured_correlation_ids.append(request.headers.get("X-Correlation-ID"))
        if request.method == "POST":
            captured_body = request.content.decode("utf-8", errors="replace")
            return httpx.Response(
                200,
                json={"job": {"job_id": "job-1", "status": "succeeded"}},
            )
        if request.method == "GET":
            return httpx.Response(
                200,
                content="# SA24D\n\nKerstin Aitman\nEdith Winlund Strandler\n".encode("utf-8"),
                headers={
                    "Content-Type": "text/markdown; charset=utf-8",
                    "Content-Disposition": 'attachment; filename="sa24d.md"',
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://convert.example") as client:
        svc = SirConvertALotClientV2(
            settings=SirConvertClientSettingsV2(
                base_url="https://convert.example",
                api_key="test-key",
                timeout_seconds=10.0,
                class_list_import_pdf_backend_strategy="pymupdf",
                class_list_import_acceleration_policy="cpu_only",
            ),
            client=client,
        )
        text = await svc.extract_text_direct(
            file_bytes=b"%PDF-1.7",
            filename="sa24d_klasslista.pdf",
            correlation_id="corr-1",
        )

    assert text.startswith("# SA24D")
    assert captured_requests == [
        ("POST", "/v2/convert/jobs"),
        ("GET", "/v2/convert/jobs/job-1/artifact"),
    ]
    assert captured_correlation_ids == ["corr-1", "corr-1"]
    assert captured_body is not None
    assert '"output_format":"md"' in captured_body
    assert '"format":"pdf"' in captured_body
    assert '"backend_strategy":"pymupdf"' in captured_body
    assert '"ocr_mode":"off"' in captured_body
    assert '"acceleration_policy":"cpu_only"' in captured_body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_text_direct_raises_when_pdf_job_reaches_failed_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests_seen: list[tuple[str, str]] = []
    captured_correlation_ids: list[str | None] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append((request.method, request.url.path))
        captured_correlation_ids.append(request.headers.get("X-Correlation-ID"))
        if request.method == "POST":
            return httpx.Response(
                202,
                json={"job": {"job_id": "job-1", "status": "queued"}},
            )
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"job": {"job_id": "job-1", "status": "failed"}},
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(sir_convert_client_v2_module.asyncio, "sleep", _no_sleep)
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
            await svc.extract_text_direct(
                file_bytes=b"%PDF-1.7",
                filename="sa24d_klasslista.pdf",
                correlation_id="corr-1",
            )

    assert excinfo.value.code == ErrorCode.SERVICE_UNAVAILABLE
    assert excinfo.value.details.get("job_id") == "job-1"
    assert excinfo.value.details.get("upstream_status") == "failed"
    assert requests_seen == [
        ("POST", "/v2/convert/jobs"),
        ("GET", "/v2/convert/jobs/job-1"),
    ]
    assert captured_correlation_ids == ["corr-1", "corr-1"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_webhook_subscription_returns_subscription_id_and_secret() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "subscription": {
                    "subscription_id": "whsub-1",
                    "callback_url": "https://consumer.example/hooks/scal",
                },
                "secret": {"value": "whsec-1"},
            },
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
        subscription = await svc.create_webhook_subscription(
            callback_url="https://consumer.example/hooks/scal",
            event_types=["job.succeeded"],
            correlation_id="corr-1",
        )

    assert subscription.subscription_id == "whsub-1"
    assert subscription.secret == "whsec-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_webhook_subscriptions_returns_subscription_summaries() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "api_version": "v2",
                "subscriptions": [
                    {
                        "subscription_id": "whsub-1",
                        "callback_url": "https://consumer.example/hooks/scal",
                        "enabled": True,
                    }
                ],
            },
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
        subscriptions = await svc.list_webhook_subscriptions(correlation_id="corr-1")

    assert len(subscriptions) == 1
    assert subscriptions[0].subscription_id == "whsub-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_sir_convert_async_http_client_supports_unix_socket_transport() -> None:
    socket_path = Path("/tmp") / f"scal-{uuid4().hex[:8]}.sock"
    seen_request_lines: list[str] = []

    async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        raw = await reader.readuntil(b"\r\n\r\n")
        seen_request_lines.append(raw.decode("utf-8", errors="replace").splitlines()[0])
        body = b'{"job":{"job_id":"job-uds","status":"queued"}}'
        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("utf-8")
            + b"Connection: close\r\n\r\n"
            + body
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    with contextlib.suppress(FileNotFoundError):
        socket_path.unlink()
    server = await asyncio.start_unix_server(_handle, path=str(socket_path))
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        settings = SirConvertClientSettingsV2(
            base_url="http://sir-convert.local",
            api_key="test-key",
            timeout_seconds=10.0,
            unix_socket_path=str(socket_path),
        )
        async with build_sir_convert_async_http_client(settings=settings) as client:
            svc = SirConvertALotClientV2(settings=settings, client=client)
            job = await svc.get_job("job-uds", correlation_id="corr-uds")
    finally:
        server.close()
        await server.wait_closed()
        serve_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await serve_task
        with contextlib.suppress(FileNotFoundError):
            socket_path.unlink()

    assert seen_request_lines == ["GET /v2/convert/jobs/job-uds HTTP/1.1"]
    assert job.job_id == "job-uds"
    assert job.status is SirConvertJobStatusV2.QUEUED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_rejects_unknown_upstream_status_at_client_boundary() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"job": {"job_id": "job-unknown", "status": "paused"}},
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
            await svc.get_job("job-unknown", correlation_id="corr-unknown")

    assert excinfo.value.code is ErrorCode.SERVICE_UNAVAILABLE
    assert excinfo.value.details == {
        "reason_code": "sir_convert_unknown_job_status",
        "status": "paused",
    }
