"""Sanitized transcript parity proof evidence helpers.

Domain purpose:
    Normalize live transcript proof responses into bounded metadata so parity
    evidence can be retained without transcript text, utterances, sensitive
    speaker names, credentials, source content, provider secrets, or media hashes.

Relationships:
    Used by the PR-0349 Playwright proof harness for ST-21-08 closeout evidence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict
from urllib.parse import urlparse

from playwright.sync_api import Response

GATEWAY_MARKER = "/sir-convert/v2/convert/jobs"
TRANSCRIPT_API_MARKER = "/api/v1/apps/documents.conversion_hub/transcripts"
INTERNAL_IDENTITY_ERROR_CODE = "auth_invalid_internal_identity"
INTERNAL_IDENTITY_REASON = "invalid_internal_identity_signature"
EVIDENCE_JSON_FILES = (
    ("network", "network.bounded.json"),
    ("console", "browser-console.bounded.json"),
)


class ScrubbedError(TypedDict, total=False):
    error_code: str | None
    message: str | None
    retryable: bool | None
    reason: str | None


class NetworkRecord(TypedDict):
    observed_at: str
    method: str
    path: str
    status: int
    content_type: str | None
    scrubbed_payload: object


class InternalIdentityBlocker(TypedDict):
    blocker_kind: Literal["sir_convert_internal_identity_rejected"]
    error_code: str
    reason: str
    http_status: int
    method: str
    path: str
    observed_at: str


@dataclass(frozen=True)
class CapturedResponse:
    response: Response
    observed_at: str


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def captured_artifact_summary(artifact_dir: Path) -> dict[str, object]:
    screenshots = sorted(path for path in artifact_dir.glob("*.png") if path.is_file())
    downloads_dir = artifact_dir / "downloads"
    downloaded_files = (
        sorted(path for path in downloads_dir.iterdir() if path.is_file())
        if downloads_dir.is_dir()
        else []
    )
    evidence_paths: list[Path] = []
    summary: dict[str, object] = {
        "artifact_dir": str(artifact_dir),
        "screenshots": [str(path) for path in screenshots],
        "downloaded_files": [str(path) for path in downloaded_files],
    }
    for key, filename in EVIDENCE_JSON_FILES:
        path = artifact_dir / filename
        if path.is_file():
            summary[key] = str(path)
            evidence_paths.append(path)
    failure_screenshot = artifact_dir / "failure.png"
    if failure_screenshot.is_file():
        summary["failure_screenshot"] = str(failure_screenshot)
    evidence_paths.extend(screenshots)
    evidence_paths.extend(downloaded_files)
    summary["captured_files"] = _existing_file_strings(evidence_paths)
    return summary


def finalize_proof_summary(
    summary: dict[str, object],
    *,
    artifact_dir: Path,
    network_records: Sequence[NetworkRecord],
) -> None:
    _record_known_blocker(summary, network_records)
    summary["artifacts"] = captured_artifact_summary(artifact_dir)


def safe_path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


def json_payload(response: Response) -> object | None:
    if "json" not in (response.headers.get("content-type") or ""):
        return None
    try:
        return response.json()
    except Exception:
        return None


def speaker_labels_from_transcript(payload: object) -> list[str]:
    labels: list[str] = []
    for segment in _transcript_segments(payload):
        if not isinstance(segment, dict):
            continue
        label = segment.get("speaker_label") or segment.get("speaker")
        if isinstance(label, str) and label not in labels:
            labels.append(label)
    return labels


def transcript_summary(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"schema_version": None, "segment_count": 0, "speaker_label_count": 0}
    language = payload.get("language")
    diarization = payload.get("diarization")
    segments = _transcript_segments(payload)
    return {
        "schema_version": payload.get("schema_version"),
        "segment_count": len(segments),
        "speaker_label_count": len(speaker_labels_from_transcript(payload)),
        "language_detected": language.get("detected") if isinstance(language, dict) else None,
        "diarization_status": diarization.get("status") if isinstance(diarization, dict) else None,
        "text_present": bool(payload.get("transcript") or payload.get("text")),
    }


def scrub_payload(path: str, payload: object) -> object:
    if not isinstance(payload, dict):
        return None
    if "error" in payload and isinstance(payload["error"], dict):
        return _scrub_error(payload["error"])
    if path.endswith("/artifacts/transcript_json"):
        return {"transcript_json": transcript_summary(payload)}
    if "job" in payload and isinstance(payload["job"], dict):
        return _scrub_job(payload["job"])
    if path.endswith("/formatter-exports"):
        return _scrub_formatter_export(payload)
    if "artifacts" in payload and isinstance(payload["artifacts"], list):
        return {
            "artifact_count": len(payload["artifacts"]),
            "artifact_keys": _artifact_keys(payload),
        }
    if path.endswith("/speaker-overlays"):
        overlays = payload.get("overlays")
        return {"overlay_count": len(overlays) if isinstance(overlays, list) else None}
    if path.endswith("/save"):
        vault = payload.get("vault_artifact")
        return {
            "saved_filename": vault.get("name") if isinstance(vault, dict) else None,
            "saved_bytes": vault.get("bytes") if isinstance(vault, dict) else None,
        }
    if "/transcripts/jobs" in path or re.search(r"/transcripts/[^/]+$", path):
        return {
            "status": payload.get("status"),
            "transcript_id_present": isinstance(payload.get("transcript_id"), str),
            "schema_version": payload.get("transcript_schema_version"),
        }
    return None


def collect_network(captured: list[CapturedResponse]) -> list[NetworkRecord]:
    records: list[NetworkRecord] = []
    for item in captured:
        response = item.response
        path = safe_path(response.url)
        records.append(
            {
                "observed_at": item.observed_at,
                "method": response.request.method,
                "path": path,
                "status": response.status,
                "content_type": response.headers.get("content-type"),
                "scrubbed_payload": scrub_payload(path, json_payload(response)),
            }
        )
    return records


def internal_identity_submit_blocker(
    records: Sequence[NetworkRecord],
) -> InternalIdentityBlocker | None:
    for record in records:
        if (
            record["method"] != "POST"
            or not record["path"].startswith(GATEWAY_MARKER)
            or record["status"] != 401
        ):
            continue
        payload = record["scrubbed_payload"]
        if not isinstance(payload, dict):
            continue
        error_code = payload.get("error_code")
        reason = payload.get("reason")
        if error_code != INTERNAL_IDENTITY_ERROR_CODE or reason != INTERNAL_IDENTITY_REASON:
            continue
        return {
            "blocker_kind": "sir_convert_internal_identity_rejected",
            "error_code": INTERNAL_IDENTITY_ERROR_CODE,
            "reason": INTERNAL_IDENTITY_REASON,
            "http_status": record["status"],
            "method": record["method"],
            "path": record["path"],
            "observed_at": record["observed_at"],
        }
    return None


def _existing_file_strings(paths: Sequence[Path]) -> list[str]:
    return [str(path) for path in paths if path.is_file()]


def _failure_from_internal_identity_blocker(
    blocker: InternalIdentityBlocker,
) -> dict[str, object]:
    return {
        "type": blocker["blocker_kind"],
        "kind": blocker["blocker_kind"],
        "http_status": blocker["http_status"],
        "error_code": blocker["error_code"],
        "reason": blocker["reason"],
        "method": blocker["method"],
        "path": blocker["path"],
        "observed_at": blocker["observed_at"],
    }


def _record_known_blocker(
    summary: dict[str, object],
    network_records: Sequence[NetworkRecord],
) -> None:
    blocker = internal_identity_submit_blocker(network_records)
    if blocker is None:
        return
    existing_failure = summary.get("failure")
    if isinstance(existing_failure, dict):
        summary["raw_failure"] = existing_failure
    summary["failure"] = _failure_from_internal_identity_blocker(blocker)
    summary["blocker_kind"] = blocker["blocker_kind"]
    summary["blocker_reason"] = blocker["reason"]
    summary["blocker_error_code"] = blocker["error_code"]
    summary["blocker"] = blocker


def capture_transcript_response(captured: list[CapturedResponse], response: Response) -> None:
    if GATEWAY_MARKER in response.url or TRANSCRIPT_API_MARKER in response.url:
        captured.append(CapturedResponse(response=response, observed_at=utc_now()))


def _transcript_segments(payload: object) -> list[object]:
    if not isinstance(payload, dict):
        return []
    segments = payload.get("segments")
    if isinstance(segments, list):
        return segments
    transcript = payload.get("transcript")
    nested = transcript.get("segments") if isinstance(transcript, dict) else []
    return nested if isinstance(nested, list) else []


def _artifact_keys(payload: dict[str, object]) -> list[object]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    return [artifact.get("artifact_key") for artifact in artifacts if isinstance(artifact, dict)]


def _safe_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value[:240]


def _scrub_error(error: dict[str, object]) -> ScrubbedError:
    details = error.get("details")
    reason = details.get("reason") if isinstance(details, dict) else None
    return {
        "error_code": _safe_text(error.get("code")),
        "message": _safe_text(error.get("message")),
        "retryable": error.get("retryable") if isinstance(error.get("retryable"), bool) else None,
        "reason": _safe_text(reason),
    }


def _scrub_job(job: dict[str, object]) -> dict[str, object]:
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else job
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "phase": progress.get("phase") or job.get("stage"),
        "last_heartbeat_at_present": bool(
            progress.get("last_heartbeat_at") or job.get("last_heartbeat_at")
        ),
        "processed_media_seconds": progress.get("audio_processed_media_seconds"),
        "total_media_seconds": progress.get("audio_total_media_seconds"),
        "percent_complete": progress.get("audio_percent_complete"),
        "current_chunk_index": progress.get("audio_current_chunk_index"),
        "total_chunks": progress.get("audio_total_chunks"),
    }


def _scrub_formatter_export(payload: dict[str, object]) -> dict[str, object]:
    requested_artifacts = payload.get("requested_artifacts")
    artifacts = payload.get("artifacts")
    return {
        "status": payload.get("status"),
        "requested_artifacts": requested_artifacts
        if isinstance(requested_artifacts, list)
        else None,
        "artifact_count": len(artifacts) if isinstance(artifacts, list) else None,
        "artifact_keys": _artifact_keys(payload),
    }
