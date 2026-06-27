"""Sir Convert producer client for product-owned transcript formatter exports.

Domain purpose:
  Call the accepted Service API v2 task-363 transcript formatter lane from
  Skriptoteket backend code and return result, manifest, and named artifact
  bytes for application-layer verification.

Relationships:
  - Implements `ConversionHubTranscriptFormatterProducerProtocol`.
  - Shares Sir Convert settings and HTTP client construction with the
    Conversion Hub v2 client.
"""

from __future__ import annotations

import asyncio
import io
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from skriptoteket.application.curated_apps.conversion_hub_transcript_formatter_contracts import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertClientSettingsV2,
)
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterProducerArtifact,
    ConversionHubTranscriptFormatterProducerProtocol,
    ConversionHubTranscriptFormatterProducerRequest,
    ConversionHubTranscriptFormatterProducerResult,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertJobStatusV2,
    parse_sir_convert_job_status_v2,
)

_ARTIFACT_KEY_BY_FORMAT = {
    ConversionHubTranscriptFormatterArtifactFormat.TXT: (
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT
    ),
    ConversionHubTranscriptFormatterArtifactFormat.MD: (
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD
    ),
    ConversionHubTranscriptFormatterArtifactFormat.VTT: (
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT
    ),
    ConversionHubTranscriptFormatterArtifactFormat.SRT: (
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT
    ),
}
_FORMATTER_EXPORT_POLL_INTERVAL_SECONDS = 0.5
_FORMATTER_EXPORT_TERMINAL_FAILURES = frozenset(
    {SirConvertJobStatusV2.FAILED, SirConvertJobStatusV2.CANCELED}
)
_STALE_IDEMPOTENCY_STATUSES = frozenset({SirConvertJobStatusV2.QUEUED})
_RECOVERY_IDEMPOTENCY_MIN_WINDOW_SECONDS = 60


@dataclass(frozen=True, slots=True)
class _ProducerJobStatus:
    """Normalized Sir Convert job status metadata used by the producer."""

    job_id: str
    status: SirConvertJobStatusV2
    error_message: str | None
    updated_at: datetime | None


class SirConvertTranscriptFormatterProducerV2(ConversionHubTranscriptFormatterProducerProtocol):
    """Submit saved transcript JSON to Sir Convert and download named artifacts."""

    def __init__(self, *, settings: SirConvertClientSettingsV2, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def create_transcript_formatter_export(
        self,
        *,
        request: ConversionHubTranscriptFormatterProducerRequest,
    ) -> ConversionHubTranscriptFormatterProducerResult:
        job_status = await self._submit_formatter_job(
            request=request,
            idempotency_key=request.idempotency_key,
        )
        if self._is_stale_idempotency_job(job_status):
            job_status = await self._submit_formatter_job(
                request=request,
                idempotency_key=_recovery_idempotency_key(
                    base_key=request.idempotency_key,
                    stale_job_id=job_status.job_id,
                    timeout_seconds=self._settings.timeout_seconds,
                ),
            )
        status, error_message = await self._wait_for_terminal_status(
            job_id=job_status.job_id,
            initial_status=job_status.status,
            initial_error_message=job_status.error_message,
            correlation_id=request.correlation_id,
        )
        if status is not SirConvertJobStatusV2.SUCCEEDED:
            return ConversionHubTranscriptFormatterProducerResult(
                sir_convert_job_id=job_status.job_id,
                status=status,
                result=None,
                artifact_manifest=None,
                artifacts={},
                error_message=error_message,
            )
        result_payload = await self._read_json_path(
            f"/v2/convert/jobs/{job_status.job_id}/result",
            correlation_id=request.correlation_id,
            message_fallback="Failed to read transcript formatter result.",
            job_id=job_status.job_id,
        )
        manifest_payload = await self._read_json_path(
            f"/v2/convert/jobs/{job_status.job_id}/artifacts",
            correlation_id=request.correlation_id,
            message_fallback="Failed to read transcript formatter artifacts.",
            job_id=job_status.job_id,
        )
        artifacts: dict[
            ConversionHubTranscriptFormatterArtifactKey,
            ConversionHubTranscriptFormatterProducerArtifact,
        ] = {}
        for requested_artifact in request.requested_artifacts:
            artifact_key = _ARTIFACT_KEY_BY_FORMAT[requested_artifact]
            artifact_response = await self._get(
                f"/v2/convert/jobs/{job_status.job_id}/artifacts/{artifact_key.value}",
                message_fallback="Failed to download transcript formatter artifact.",
                job_id=job_status.job_id,
                headers=self._headers(correlation_id=request.correlation_id),
            )
            if artifact_response.status_code != 200:
                raise _extract_service_error(
                    artifact_response,
                    message_fallback="Failed to download transcript formatter artifact.",
                    job_id=job_status.job_id,
                )
            artifacts[artifact_key] = ConversionHubTranscriptFormatterProducerArtifact(
                artifact_key=artifact_key,
                content_type=artifact_response.headers.get(
                    "content-type",
                    "application/octet-stream",
                ),
                content=artifact_response.content,
            )
        return ConversionHubTranscriptFormatterProducerResult(
            sir_convert_job_id=job_status.job_id,
            status=status,
            result=result_payload,
            artifact_manifest=manifest_payload,
            artifacts=artifacts,
            error_message=None,
        )

    async def _submit_formatter_job(
        self,
        *,
        request: ConversionHubTranscriptFormatterProducerRequest,
        idempotency_key: str,
    ) -> _ProducerJobStatus:
        response = await self._post(
            "/v2/convert/jobs",
            message_fallback="Failed to create transcript formatter export.",
            params={"wait_seconds": request.wait_seconds},
            headers=self._headers(
                idempotency_key=idempotency_key,
                correlation_id=request.correlation_id,
            ),
            data={"job_spec": json.dumps(request.job_spec, separators=(",", ":"), sort_keys=True)},
            files={
                "file": (
                    request.filename,
                    io.BytesIO(request.file_bytes),
                    request.content_type,
                )
            },
        )
        if response.status_code not in {200, 202}:
            raise _extract_service_error(
                response,
                message_fallback="Failed to create transcript formatter export.",
            )
        return _read_job_status(response.json())

    def _is_stale_idempotency_job(self, job_status: _ProducerJobStatus) -> bool:
        if job_status.status not in _STALE_IDEMPOTENCY_STATUSES:
            return False
        if job_status.updated_at is None:
            return False
        stale_after = max(
            self._settings.timeout_seconds,
            _RECOVERY_IDEMPOTENCY_MIN_WINDOW_SECONDS,
        )
        return (datetime.now(UTC) - job_status.updated_at).total_seconds() >= stale_after

    async def _wait_for_terminal_status(
        self,
        *,
        job_id: str,
        initial_status: SirConvertJobStatusV2,
        initial_error_message: str | None,
        correlation_id: str | None,
    ) -> tuple[SirConvertJobStatusV2, str | None]:
        current_status = initial_status
        current_error_message = initial_error_message
        deadline = time.monotonic() + self._settings.timeout_seconds

        while True:
            if current_status is SirConvertJobStatusV2.SUCCEEDED:
                return current_status, current_error_message
            if current_status in _FORMATTER_EXPORT_TERMINAL_FAILURES:
                return current_status, current_error_message
            if time.monotonic() >= deadline:
                raise DomainError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Sir Convert transcript formatter export timed out.",
                    details={"job_id": job_id, "upstream_status": current_status.value},
                )

            await asyncio.sleep(_FORMATTER_EXPORT_POLL_INTERVAL_SECONDS)
            payload = await self._read_json_path(
                f"/v2/convert/jobs/{job_id}",
                correlation_id=correlation_id,
                message_fallback="Failed to read transcript formatter job status.",
                job_id=job_id,
            )
            status_snapshot = _read_job_status(payload)
            current_status = status_snapshot.status
            current_error_message = status_snapshot.error_message

    def _headers(
        self,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, str]:
        headers = {"X-API-Key": self._settings.api_key}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if correlation_id is not None:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    async def _post(
        self,
        path: str,
        *,
        message_fallback: str,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            return await self._client.post(path, **kwargs)
        except httpx.RequestError as exc:
            raise _extract_transport_error(
                exc,
                message_fallback=message_fallback,
                job_id=job_id,
            ) from exc

    async def _get(
        self,
        path: str,
        *,
        message_fallback: str,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            return await self._client.get(path, **kwargs)
        except httpx.RequestError as exc:
            raise _extract_transport_error(
                exc,
                message_fallback=message_fallback,
                job_id=job_id,
            ) from exc

    async def _read_json_path(
        self,
        path: str,
        *,
        correlation_id: str | None,
        message_fallback: str,
        job_id: str,
    ) -> dict[str, object]:
        response = await self._get(
            path,
            message_fallback=message_fallback,
            job_id=job_id,
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 200:
            raise _extract_service_error(
                response,
                message_fallback=message_fallback,
                job_id=job_id,
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=message_fallback,
                details={"job_id": job_id},
            )
        return payload


def _read_job_status(payload: object) -> _ProducerJobStatus:
    if not isinstance(payload, dict):
        raise _malformed_submit_response()
    job_obj = payload.get("job")
    if not isinstance(job_obj, dict):
        raise _malformed_submit_response()
    job_id_obj = job_obj.get("job_id")
    status_obj = job_obj.get("status")
    if not isinstance(job_id_obj, str) or not isinstance(status_obj, str):
        raise _malformed_submit_response()
    error_message = None
    error_obj = job_obj.get("error")
    if isinstance(error_obj, str):
        error_message = error_obj
    elif isinstance(error_obj, dict) and isinstance(error_obj.get("message"), str):
        error_message = error_obj["message"]
    return _ProducerJobStatus(
        job_id=job_id_obj,
        status=parse_sir_convert_job_status_v2(status_obj),
        error_message=error_message,
        updated_at=_read_datetime(job_obj.get("updated_at")),
    )


def _read_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _recovery_idempotency_key(
    *,
    base_key: str,
    stale_job_id: str,
    timeout_seconds: float,
) -> str:
    window_seconds = max(int(timeout_seconds), _RECOVERY_IDEMPOTENCY_MIN_WINDOW_SECONDS)
    window = int(time.time() // window_seconds)
    return f"{base_key}:recover:{stale_job_id}:{window}"


def _malformed_submit_response() -> DomainError:
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Sir Convert transcript formatter response is malformed.",
        details={"upstream": "sir_convert_transcript_formatter_export"},
    )


def _extract_transport_error(
    exc: httpx.RequestError,
    *,
    message_fallback: str,
    job_id: str | None = None,
) -> DomainError:
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=message_fallback,
        details={
            "job_id": job_id,
            "upstream_error_type": type(exc).__name__,
        },
    )


def _extract_service_error(
    response: httpx.Response,
    *,
    message_fallback: str,
    job_id: str | None = None,
) -> DomainError:
    payload: object
    try:
        payload = response.json()
    except ValueError:
        payload = None
    upstream_message = None
    upstream_code = None
    if isinstance(payload, dict):
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            message_obj = error_obj.get("message")
            code_obj = error_obj.get("code")
            upstream_message = message_obj if isinstance(message_obj, str) else None
            upstream_code = code_obj if isinstance(code_obj, str) else None
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=upstream_message or message_fallback,
        details={
            "job_id": job_id,
            "upstream_status_code": response.status_code,
            "upstream_code": upstream_code,
        },
    )
