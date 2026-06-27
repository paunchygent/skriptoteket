"""Protocols and typed envelopes for Sir Convert-a-Lot v2 integration.

Purpose:
  Provide a typed, testable seam for calling Sir Convert-a-Lot v2 from Skriptoteket.

Relationships:
  - Implemented by `infrastructure/.../conversion_hub/sir_convert_client_v2.py`.
  - Used by the Conversion Hub curated app API routes to submit/poll/download jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol

from skriptoteket.domain.errors import DomainError, ErrorCode


class SirConvertJobStatusV2(StrEnum):
    """Canonical Sir Convert-a-Lot v2 upstream job lifecycle."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


def parse_sir_convert_job_status_v2(status: str) -> SirConvertJobStatusV2:
    """Parse one Sir Convert v2 job status and fail closed on vocabulary drift."""

    try:
        return SirConvertJobStatusV2(status)
    except ValueError as exc:
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Sir Convert-a-Lot v2 returned an unsupported job status.",
            details={
                "reason_code": "sir_convert_unknown_job_status",
                "status": status,
            },
        ) from exc


@dataclass(frozen=True, slots=True)
class SirConvertJobV2:
    job_id: str
    status: SirConvertJobStatusV2


@dataclass(frozen=True, slots=True)
class SirConvertSubmittedJobV2(SirConvertJobV2):
    idempotent_replay: bool


@dataclass(frozen=True, slots=True)
class SirConvertArtifactV2:
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class SirConvertArtifactOutcomeV2:
    job_id: str
    status: Literal["succeeded"]
    artifact: SirConvertArtifactV2


@dataclass(frozen=True, slots=True)
class SirConvertSubmitRequestV2:
    filename: str
    content_type: str
    file_bytes: bytes
    job_spec: dict[str, object]
    idempotency_key: str
    wait_seconds: int
    correlation_id: str | None
    resources_filename: str | None = None
    resources_bytes: bytes | None = None
    reference_docx_filename: str | None = None
    reference_docx_bytes: bytes | None = None


@dataclass(frozen=True, slots=True)
class SirConvertWebhookSubscriptionV2:
    subscription_id: str
    callback_url: str
    secret: str


@dataclass(frozen=True, slots=True)
class SirConvertWebhookSubscriptionSummaryV2:
    subscription_id: str
    callback_url: str


class SirConvertALotClientV2Protocol(Protocol):
    async def extract_text_direct(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> str:
        """Extract text from a file via the Sir Convert v2 PDF-to-Markdown job flow."""
        ...

    async def submit_job(
        self,
        *,
        request: SirConvertSubmitRequestV2,
    ) -> SirConvertSubmittedJobV2: ...

    async def get_job(self, job_id: str, *, correlation_id: str | None) -> SirConvertJobV2: ...

    async def download_artifact(
        self, job_id: str, *, correlation_id: str | None
    ) -> SirConvertArtifactOutcomeV2: ...

    async def download_named_artifact(
        self,
        job_id: str,
        artifact_key: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2: ...

    async def create_webhook_subscription(
        self,
        *,
        callback_url: str,
        event_types: list[str],
        correlation_id: str | None,
    ) -> SirConvertWebhookSubscriptionV2: ...

    async def list_webhook_subscriptions(
        self,
        *,
        correlation_id: str | None,
    ) -> list[SirConvertWebhookSubscriptionSummaryV2]: ...

    async def delete_webhook_subscription(
        self,
        subscription_id: str,
        *,
        correlation_id: str | None,
    ) -> None: ...
