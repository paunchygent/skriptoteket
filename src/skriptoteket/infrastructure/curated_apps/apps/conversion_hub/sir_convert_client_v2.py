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

import asyncio
import io
import json
import time
from dataclasses import dataclass
from uuid import uuid4

import httpx

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertArtifactV2,
    SirConvertJobV2,
    SirConvertSubmitRequestV2,
    SirConvertSubmittedJobV2,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
)


@dataclass(frozen=True, slots=True)
class SirConvertClientSettingsV2:
    base_url: str
    api_key: str
    timeout_seconds: float
    unix_socket_path: str | None = None
    class_list_import_pdf_backend_strategy: str = "pymupdf"
    class_list_import_acceleration_policy: str = "cpu_only"


_PDF_TEXT_EXTRACTION_WAIT_SECONDS = 0
_PDF_TEXT_EXTRACTION_POLL_INTERVAL_SECONDS = 0.5
_PDF_TEXT_EXTRACTION_TERMINAL_FAILURES = frozenset({"failed", "canceled", "cancelled"})


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


def _build_pdf_text_extraction_job_spec(
    *,
    filename: str,
    backend_strategy: str,
    acceleration_policy: str,
) -> dict[str, object]:
    """Build the canonical Sir Convert v2 job spec for PDF-to-Markdown extraction."""

    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": "pdf"},
        "conversion": {
            "output_format": "md",
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "pdf_options": {
            "backend_strategy": backend_strategy,
            "ocr_mode": "off",
            "ocr_engine": "auto",
            "ocr_languages": [],
            "table_mode": "accurate",
            "normalize": "strict",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def build_sir_convert_async_http_client(
    *,
    settings: SirConvertClientSettingsV2,
) -> httpx.AsyncClient:
    """Build the Sir Convert HTTP client with optional same-host Unix-socket transport."""

    if settings.unix_socket_path:
        transport = httpx.AsyncHTTPTransport(uds=settings.unix_socket_path)
        return httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            transport=transport,
        )
    return httpx.AsyncClient(
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
    )


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

    async def _wait_for_text_extraction_job(
        self,
        *,
        job_id: str,
        initial_status: str,
        correlation_id: str | None,
    ) -> None:
        """Poll one PDF-to-Markdown job until it succeeds or fails."""

        current_status = initial_status
        deadline = time.monotonic() + self._settings.timeout_seconds

        while True:
            if current_status == "succeeded":
                return
            if current_status in _PDF_TEXT_EXTRACTION_TERMINAL_FAILURES:
                raise DomainError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Sir Convert-a-Lot v2 PDF extraction job failed.",
                    details={"job_id": job_id, "upstream_status": current_status},
                )
            if time.monotonic() >= deadline:
                raise DomainError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Sir Convert-a-Lot v2 PDF extraction timed out.",
                    details={"job_id": job_id, "upstream_status": current_status},
                )

            await asyncio.sleep(_PDF_TEXT_EXTRACTION_POLL_INTERVAL_SECONDS)
            current_job = await self.get_job(job_id, correlation_id=correlation_id)
            current_status = current_job.status

    async def submit_job(self, *, request: SirConvertSubmitRequestV2) -> SirConvertSubmittedJobV2:
        files: dict[str, tuple[str, io.BytesIO, str]] = {
            "file": (
                request.filename,
                io.BytesIO(request.file_bytes),
                request.content_type,
            )
        }
        if request.resources_filename is not None and request.resources_bytes is not None:
            files["resources"] = (
                request.resources_filename,
                io.BytesIO(request.resources_bytes),
                "application/zip",
            )
        if request.reference_docx_filename is not None and request.reference_docx_bytes is not None:
            files["reference_docx"] = (
                request.reference_docx_filename,
                io.BytesIO(request.reference_docx_bytes),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        response = await self._client.post(
            "/v2/convert/jobs",
            params={"wait_seconds": request.wait_seconds},
            headers=self._headers(
                idempotency_key=request.idempotency_key,
                correlation_id=request.correlation_id,
            ),
            data={
                "job_spec": json.dumps(request.job_spec, separators=(",", ":"), sort_keys=True),
            },
            files=files,
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

    async def create_webhook_subscription(
        self,
        *,
        callback_url: str,
        event_types: list[str],
        correlation_id: str | None,
    ) -> SirConvertWebhookSubscriptionV2:
        response = await self._client.post(
            "/v2/push/webhooks/subscriptions",
            headers=self._headers(correlation_id=correlation_id),
            json={
                "callback_url": callback_url,
                "event_types": event_types,
                "enabled": True,
            },
        )
        if response.status_code != 201:
            raise _extract_service_error(
                response,
                message_fallback="Failed to create Sir Convert webhook subscription.",
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Sir Convert-a-Lot v2 returned an invalid webhook payload.",
                details={},
            )
        subscription = payload.get("subscription")
        secret = payload.get("secret")
        if not isinstance(subscription, dict) or not isinstance(secret, dict):
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Sir Convert-a-Lot v2 webhook response is missing subscription details.",
                details={},
            )

        subscription_id = subscription.get("subscription_id")
        response_callback_url = subscription.get("callback_url")
        secret_value = secret.get("value")
        if (
            not isinstance(subscription_id, str)
            or subscription_id == ""
            or not isinstance(response_callback_url, str)
            or response_callback_url == ""
            or not isinstance(secret_value, str)
            or secret_value == ""
        ):
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Sir Convert-a-Lot v2 webhook response is incomplete.",
                details={},
            )

        return SirConvertWebhookSubscriptionV2(
            subscription_id=subscription_id,
            callback_url=response_callback_url,
            secret=secret_value,
        )

    async def list_webhook_subscriptions(
        self,
        *,
        correlation_id: str | None,
    ) -> list[SirConvertWebhookSubscriptionSummaryV2]:
        response = await self._client.get(
            "/v2/push/webhooks/subscriptions",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 200:
            raise _extract_service_error(
                response,
                message_fallback="Failed to list Sir Convert webhook subscriptions.",
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Sir Convert-a-Lot v2 returned an invalid webhook list payload.",
                details={},
            )
        subscriptions = payload.get("subscriptions")
        if not isinstance(subscriptions, list):
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Sir Convert-a-Lot v2 webhook list is missing subscriptions.",
                details={},
            )

        result: list[SirConvertWebhookSubscriptionSummaryV2] = []
        for item in subscriptions:
            if not isinstance(item, dict):
                continue
            subscription_id = item.get("subscription_id")
            callback_url = item.get("callback_url")
            if (
                isinstance(subscription_id, str)
                and subscription_id
                and isinstance(callback_url, str)
            ):
                result.append(
                    SirConvertWebhookSubscriptionSummaryV2(
                        subscription_id=subscription_id,
                        callback_url=callback_url,
                    )
                )
        return result

    async def delete_webhook_subscription(
        self,
        subscription_id: str,
        *,
        correlation_id: str | None,
    ) -> None:
        response = await self._client.delete(
            f"/v2/push/webhooks/subscriptions/{subscription_id}",
            headers=self._headers(correlation_id=correlation_id),
        )
        if response.status_code != 204:
            raise _extract_service_error(
                response,
                message_fallback="Failed to delete Sir Convert webhook subscription.",
            )

    async def extract_text_direct(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> str:
        submitted = await self.submit_job(
            request=SirConvertSubmitRequestV2(
                filename=filename,
                content_type="application/pdf",
                file_bytes=file_bytes,
                job_spec=_build_pdf_text_extraction_job_spec(
                    filename=filename,
                    backend_strategy=self._settings.class_list_import_pdf_backend_strategy,
                    acceleration_policy=self._settings.class_list_import_acceleration_policy,
                ),
                idempotency_key=f"class-list-import-pdf-{uuid4().hex}",
                wait_seconds=_PDF_TEXT_EXTRACTION_WAIT_SECONDS,
                correlation_id=correlation_id,
            )
        )
        await self._wait_for_text_extraction_job(
            job_id=submitted.job_id,
            initial_status=submitted.status,
            correlation_id=correlation_id,
        )
        artifact = await self.download_artifact(submitted.job_id, correlation_id=correlation_id)

        return artifact.artifact.content.decode("utf-8", errors="replace")
