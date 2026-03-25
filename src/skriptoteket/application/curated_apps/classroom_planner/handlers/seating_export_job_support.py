"""Support helpers for classroom-planner seating export jobs.

Purpose:
    Keep reusable export-job status mapping, Sir Convert request shaping,
    renderer resource bundling, and webhook verification separate from the main
    application handlers so the orchestration modules stay small and focused.

Relationships:
    - Used by `seating_export_jobs.py`.
    - Depends on application export-job models and Vault repositories only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Iterable
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJob,
    SeatingExportJobResult,
    SeatingExportJobStatus,
    SeatingExportPaperSize,
    SeatingExportVaultArtifact,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

_SIGNATURE_HEADER = "x-scal-webhook-signature"
_TIMESTAMP_HEADER = "x-scal-webhook-timestamp"


async def build_job_result(
    *,
    job: SeatingExportJob,
    vault_files: VaultFileRepositoryProtocol | None,
) -> SeatingExportJobResult:
    """Build the public job result from one persisted export job."""

    vault_artifact = None
    if job.vault_file_id is not None and vault_files is not None:
        vault_file = await vault_files.get_by_id(file_id=job.vault_file_id)
        if vault_file is not None:
            vault_artifact = SeatingExportVaultArtifact(
                file_id=vault_file.id,
                name=vault_file.name,
                bytes=vault_file.bytes,
                created_at=vault_file.created_at,
            )
    download_url = (
        f"/api/v1/apps/classroom.group-seating-studio/exports/jobs/{job.id}/download"
        if vault_artifact is not None
        else None
    )
    return SeatingExportJobResult(
        job_id=job.id,
        draft_id=job.draft_id,
        export_kind=job.export_kind,
        layout_id=job.layout_id,
        paper_size=job.paper_size,
        status=job.status,
        created_at=job.created_at,
        download_url=download_url,
        vault_artifact=vault_artifact,
        error=job.error_message,
    )


def map_upstream_status(status: str) -> SeatingExportJobStatus:
    """Map an upstream Sir Convert status to the public export-job status."""

    if status in {"queued", "pending"}:
        return SeatingExportJobStatus.SUBMITTED
    if status in {"running", "resuming"}:
        return SeatingExportJobStatus.PROCESSING
    if status == "succeeded":
        return SeatingExportJobStatus.PROCESSING
    return SeatingExportJobStatus.FAILED


def build_job_spec(
    *,
    paper_size: SeatingExportPaperSize,
    source_filename: str,
    css_filename: str,
) -> dict[str, object]:
    """Build the Sir Convert v2 job spec for one poster export."""

    del paper_size
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": source_filename, "format": "html"},
        "conversion": {
            "output_format": "pdf",
            "css_filenames": [css_filename],
            "page_css_mode": "author_owned",
            "template": None,
            "reference_docx_filename": None,
        },
        "pdf_options": None,
        "execution": None,
        "retention": {"pin": False},
    }


def build_resources_zip(*, files: Iterable[tuple[str, bytes]]) -> bytes:
    """Build a deterministic resources zip for renderer-owned poster assets."""

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for filename, content in sorted(files, key=lambda item: item[0]):
            info = ZipInfo(filename=filename)
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return buffer.getvalue()


def verify_webhook_signature(*, secret: str, headers: dict[str, str], raw_body: bytes) -> None:
    """Verify the Sir Convert webhook signature headers against the raw body."""

    normalized_headers = {key.lower(): value for key, value in headers.items()}
    signature_header = normalized_headers.get(_SIGNATURE_HEADER)
    timestamp = normalized_headers.get(_TIMESTAMP_HEADER)
    if not signature_header or not timestamp:
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Ogiltig webhook-signatur.",
            details={},
        )
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature_header, f"v1={expected}"):
        raise DomainError(
            code=ErrorCode.UNAUTHORIZED,
            message="Ogiltig webhook-signatur.",
            details={},
        )


def parse_webhook_payload(raw_body: bytes) -> dict[str, str]:
    """Parse the minimal webhook payload fields needed for export completion."""

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise validation_error("Ogiltig webhook-payload.") from exc
    if not isinstance(payload, dict):
        raise validation_error("Ogiltig webhook-payload.")
    job_id = payload.get("job_id")
    event_type = payload.get("event_type")
    if not isinstance(job_id, str) or not isinstance(event_type, str):
        raise validation_error("Ogiltig webhook-payload.")
    return {"job_id": job_id, "event_type": event_type}
