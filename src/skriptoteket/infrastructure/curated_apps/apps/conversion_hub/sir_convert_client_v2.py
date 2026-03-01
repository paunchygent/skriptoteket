"""Async Sir Convert-a-Lot v2 client used by Skriptoteket's Conversion Hub curated app.

Purpose:
  Provide a small, typed wrapper around Sir Convert-a-Lot v2 endpoints
  (`/v2/convert/jobs/*`) so Skriptoteket can orchestrate submit/poll/download
  without embedding conversion engines locally.

Relationships:
  - Implements `skriptoteket.protocols.sir_convert_a_lot_v2.SirConvertALotClientV2Protocol`.
  - Used by `web/api/v1/apps_conversion_hub.py` (via Dishka DI).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import IO

import httpx

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertArtifactV2,
    SirConvertJobV2,
    SirConvertSubmittedJobV2,
)


@dataclass(frozen=True, slots=True)
class SirConvertClientSettingsV2:
    base_url: str
    api_key: str
    timeout_seconds: float


def _extract_service_error(
    response: httpx.Response, *, message_fallback: str, job_id: str | None = None
) -> DomainError:
    payload: object
    try:
        payload = response.json()
    except ValueError:
        payload = None

    upstream_code: str | None = None
    upstream_message: str | None = None
    upstream_retryable: bool | None = None
    upstream_details: object | None = None

    if isinstance(payload, dict):
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            upstream_code_obj = error_obj.get("code")
            upstream_message_obj = error_obj.get("message")
            upstream_retryable_obj = error_obj.get("retryable")
            upstream_details_obj = error_obj.get("details")
            upstream_code = upstream_code_obj if isinstance(upstream_code_obj, str) else None
            upstream_message = (
                upstream_message_obj if isinstance(upstream_message_obj, str) else None
            )
            upstream_retryable = (
                upstream_retryable_obj if isinstance(upstream_retryable_obj, bool) else None
            )
            upstream_details = upstream_details_obj

    details: dict[str, object] = {
        "upstream_status_code": response.status_code,
        "upstream_code": upstream_code,
        "upstream_message": upstream_message,
        "upstream_retryable": upstream_retryable,
        "upstream_details": upstream_details,
        "job_id": job_id,
    }
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=upstream_message or message_fallback,
        details=details,
    )


def _read_job_id_and_status(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Sir Convert-a-Lot v2 returned a non-object JSON payload.",
            details={},
        )
    job_obj = payload.get("job")
    if not isinstance(job_obj, dict):
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Sir Convert-a-Lot v2 response is missing the 'job' object.",
            details={},
        )
    job_id_obj = job_obj.get("job_id")
    status_obj = job_obj.get("status")
    if not isinstance(job_id_obj, str) or not isinstance(status_obj, str):
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Sir Convert-a-Lot v2 response is missing 'job_id' or 'status'.",
            details={},
        )
    return job_id_obj, status_obj


class SirConvertALotClientV2:
    def __init__(self, *, settings: SirConvertClientSettingsV2, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    def _headers(
        self, *, idempotency_key: str | None = None, correlation_id: str | None = None
    ) -> dict[str, str]:
        headers = {"X-API-Key": self._settings.api_key}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if correlation_id is not None:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    async def submit_job(
        self,
        *,
        filename: str,
        content_type: str,
        file_handle: IO[bytes],
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        correlation_id: str | None,
    ) -> SirConvertSubmittedJobV2:
        response = await self._client.post(
            "/v2/convert/jobs",
            params={"wait_seconds": wait_seconds},
            headers=self._headers(idempotency_key=idempotency_key, correlation_id=correlation_id),
            data={
                "job_spec": json.dumps(job_spec, separators=(",", ":"), sort_keys=True),
            },
            files={"file": (filename, file_handle, content_type)},
        )

        if response.status_code not in {200, 202}:
            raise _extract_service_error(
                response, message_fallback="Failed to submit v2 conversion job."
            )

        payload: object = response.json()
        job_id, status = _read_job_id_and_status(payload)
        idempotent_replay = response.headers.get("X-Idempotent-Replay", "").lower() == "true"
        return SirConvertSubmittedJobV2(
            job_id=job_id, status=status, idempotent_replay=idempotent_replay
        )

    async def get_job(self, job_id: str, *, correlation_id: str | None) -> SirConvertJobV2:
        response = await self._client.get(
            f"/v2/convert/jobs/{job_id}",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 200:
            raise _extract_service_error(
                response,
                message_fallback="Failed to read v2 job status.",
                job_id=job_id,
            )
        payload: object = response.json()
        current_job_id, status = _read_job_id_and_status(payload)
        return SirConvertJobV2(job_id=current_job_id, status=status)

    async def download_artifact(
        self, job_id: str, *, correlation_id: str | None
    ) -> SirConvertArtifactOutcomeV2:
        response = await self._client.get(
            f"/v2/convert/jobs/{job_id}/artifact",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 200:
            raise _extract_service_error(
                response,
                message_fallback="Failed to download v2 artifact.",
                job_id=job_id,
            )

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        disposition = response.headers.get("Content-Disposition", "")
        filename = "artifact"
        if "filename=" in disposition:
            # best-effort: rely on upstream quoting behavior (we treat this as UI sugar only)
            _, _, after = disposition.partition("filename=")
            filename = after.strip().strip('"') or filename

        return SirConvertArtifactOutcomeV2(
            job_id=job_id,
            status="succeeded",
            artifact=SirConvertArtifactV2(
                filename=filename,
                content_type=content_type,
                content=response.content,
            ),
        )
