"""Sir Convert Gateway proof evidence helpers.

Domain purpose:
    Capture and validate redacted HuleEdu Gateway evidence for Sir Convert
    Service API v2 browser submissions.

Relationships:
    Used by Audio Transcription browser proofs to assert service-owned
    retryable-failed idempotency reattempt behavior without caller-side reruns.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from playwright.sync_api import Page, Request, Response

from scripts._transcript_parity_evidence import safe_path, transcript_summary, utc_now

ProofPhase = Literal["setup", "precondition", "replay", "complete"]
GATEWAY_PATH_MARKER = "/sir-convert/v2/convert/jobs"
CREATE_PATH_PATTERN = re.compile(r"^/sir-convert/v2/convert/jobs(?:\?wait_seconds=\d+)?$")


@dataclass
class GatewayCapture:
    """Mutable redacted Gateway capture state for one browser proof run."""

    phase: ProofPhase = "setup"
    request_records: list[dict[str, object]] = field(default_factory=list)
    response_records: list[dict[str, object]] = field(default_factory=list)
    console_records: list[dict[str, str]] = field(default_factory=list)

    def attach(self, page: Page) -> None:
        """Attach request, response, console, and page-error listeners."""

        page.on("request", lambda request: self.capture_request(request))
        page.on("response", lambda response: self.capture_response(response))
        page.on(
            "console",
            lambda message: self.console_records.append(
                {"type": message.type, "text": message.text[:300]}
            ),
        )
        page.on(
            "pageerror",
            lambda error: self.console_records.append(
                {"type": "pageerror", "text": str(error)[:300]}
            ),
        )

    def create_request_records(self, *, phase: ProofPhase) -> list[dict[str, object]]:
        """Return retained create-job request records for one proof phase."""

        return [
            record
            for record in self.request_records
            if record.get("phase") == phase
            and record.get("method") == "POST"
            and isinstance(record.get("path"), str)
            and CREATE_PATH_PATTERN.match(str(record["path"]))
        ]

    def create_response_records(self, *, phase: ProofPhase) -> list[dict[str, object]]:
        """Return retained create-job response records for one proof phase."""

        return [
            record
            for record in self.response_records
            if record.get("phase") == phase
            and record.get("method") == "POST"
            and isinstance(record.get("path"), str)
            and CREATE_PATH_PATTERN.match(str(record["path"]))
        ]

    def capture_request(self, request: Request) -> None:
        """Capture one redacted create-job request."""

        path = safe_path(request.url)
        if request.method != "POST" or not CREATE_PATH_PATTERN.match(path):
            return
        self.request_records.append(
            {
                "phase": self.phase,
                "observed_at": utc_now(),
                "method": request.method,
                "path": path,
                "headers": selected_request_headers(request.headers),
            }
        )

    def capture_response(self, response: Response) -> None:
        """Capture one redacted Gateway response."""

        path = safe_path(response.url)
        if GATEWAY_PATH_MARKER not in path:
            return
        self.response_records.append(
            {
                "phase": self.phase,
                "observed_at": utc_now(),
                "method": response.request.method,
                "path": path,
                "status": response.status,
                "headers": {
                    "x-idempotent-replay": response.headers.get("x-idempotent-replay"),
                    "content-type": response.headers.get("content-type"),
                },
                "request_headers": selected_request_headers(response.request.headers),
                "payload": sanitize_gateway_payload(path, json_payload(response)),
            }
        )


def selected_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Keep proof-relevant request headers without credentials or cookies."""

    selected: dict[str, str] = {}
    for key in ("idempotency-key", "x-correlation-id", "origin", "referer"):
        value = headers.get(key)
        if value:
            selected[key] = value
    return selected


def json_payload(response: Response) -> object | None:
    """Return JSON response content when available."""

    if "json" not in (response.headers.get("content-type") or ""):
        return None
    try:
        return response.json()
    except Exception:
        return None


def sanitize_gateway_payload(path: str, payload: object) -> object:
    """Retain bounded Service API v2 evidence without source or transcript text."""

    if not isinstance(payload, dict):
        return None
    if path.endswith("/artifacts/transcript_json"):
        return {"transcript_json": transcript_summary(payload)}
    if "error" in payload and isinstance(payload["error"], dict):
        return _scrub_error(payload["error"])
    if "job" in payload and isinstance(payload["job"], dict):
        sanitized: dict[str, object] = {"job": _scrub_job(payload["job"])}
        idempotency = payload.get("idempotency")
        if isinstance(idempotency, dict):
            sanitized["idempotency"] = _scrub_idempotency(idempotency)
        return sanitized
    if "artifacts" in payload and isinstance(payload["artifacts"], list):
        return {
            "artifacts": [
                _scrub_artifact(artifact)
                for artifact in payload["artifacts"]
                if isinstance(artifact, dict)
            ]
        }
    if "result" in payload and isinstance(payload["result"], dict):
        return {"result": _scrub_result(payload["result"])}
    return None


def assert_retryable_reattempt_evidence(
    *,
    capture: GatewayCapture,
    precondition_job_id: str,
    precondition_idempotency_key: str | None = None,
) -> dict[str, object]:
    """Assert one service-owned retryable reattempt and summarize retained proof."""

    replay_requests = capture.create_request_records(phase="replay")
    replay_creates = capture.create_response_records(phase="replay")
    if len(replay_requests) != 1:
        raise AssertionError(f"Replay emitted {len(replay_requests)} create-job POSTs.")
    if len(replay_creates) != 1:
        raise AssertionError(f"Replay retained {len(replay_creates)} create responses.")
    replay_job_id = job_id_from_create_response(replay_creates[0])
    idempotency = _reattempt_idempotency(
        replay_creates[0],
        precondition_job_id=precondition_job_id,
    )
    same_key = _same_idempotency_key(
        replay_requests[0],
        precondition_idempotency_key=precondition_idempotency_key,
    )
    return {
        "replay_create_post_count": len(replay_requests),
        "same_idempotency_key_as_precondition": same_key,
        "precondition_job_id": precondition_job_id,
        "replay_job_id": replay_job_id,
        "service_reattempt": {
            "state": idempotency.get("state"),
            "attempt_count": idempotency.get("attempt_count"),
            "active_job_id": idempotency.get("active_job_id"),
            "reattempt_of_job_id": idempotency.get("reattempt_of_job_id"),
            "previous_attempts": idempotency.get("previous_attempts"),
        },
        "artifact_fetches": artifact_fetch_evidence(capture.response_records, replay_job_id),
    }


def job_id_from_create_response(record: Mapping[str, object]) -> str:
    """Extract the Service API v2 job id from a retained create response."""

    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise AssertionError("Create response retained no payload.")
    job = payload.get("job")
    if not isinstance(job, dict) or not isinstance(job.get("job_id"), str):
        raise AssertionError("Create response retained no job id.")
    return job["job_id"]


def artifact_fetch_evidence(
    response_records: Sequence[dict[str, object]],
    job_id: str,
) -> dict[str, object]:
    """Assert result, manifest, and transcript JSON fetches were retained."""

    result_fetch = _matching_gets(response_records, f"{GATEWAY_PATH_MARKER}/{job_id}/result")
    manifest_fetch = _matching_gets(response_records, f"{GATEWAY_PATH_MARKER}/{job_id}/artifacts")
    transcript_json_fetch = _matching_gets(
        response_records,
        f"{GATEWAY_PATH_MARKER}/{job_id}/artifacts/transcript_json",
    )
    if not result_fetch:
        raise AssertionError("Replay success did not retain a result fetch.")
    if not manifest_fetch:
        raise AssertionError("Replay success did not retain an artifacts manifest fetch.")
    if not transcript_json_fetch:
        raise AssertionError("Replay success did not retain transcript_json fetch.")
    transcript_payload = transcript_json_fetch[-1].get("payload")
    transcript_json = (
        transcript_payload.get("transcript_json") if isinstance(transcript_payload, dict) else None
    )
    return {
        "result_fetch_status": result_fetch[-1]["status"],
        "manifest_fetch_status": manifest_fetch[-1]["status"],
        "transcript_json_fetch_status": transcript_json_fetch[-1]["status"],
        "transcript_json": transcript_json,
    }


def _reattempt_idempotency(
    record: Mapping[str, object],
    *,
    precondition_job_id: str,
) -> Mapping[str, object]:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise AssertionError("Replay create response retained no payload.")
    idempotency = payload.get("idempotency")
    if not isinstance(idempotency, dict):
        raise AssertionError("Replay create response retained no idempotency metadata.")
    if idempotency.get("state") != "service_reattempt":
        raise AssertionError(f"Replay idempotency state was {idempotency.get('state')!r}.")
    if idempotency.get("reattempt_of_job_id") != precondition_job_id:
        raise AssertionError("Replay idempotency lineage did not point at the failed attempt.")
    _assert_previous_attempt(idempotency, precondition_job_id=precondition_job_id)
    return idempotency


def _assert_previous_attempt(
    idempotency: Mapping[str, object],
    *,
    precondition_job_id: str,
) -> None:
    previous_attempts = idempotency.get("previous_attempts")
    if not isinstance(previous_attempts, list) or not previous_attempts:
        raise AssertionError("Replay idempotency metadata did not retain previous attempts.")
    failed_attempts = [
        item
        for item in previous_attempts
        if isinstance(item, dict)
        and item.get("job_id") == precondition_job_id
        and item.get("status") == "failed"
        and item.get("failure_retryable") is True
    ]
    if not failed_attempts:
        raise AssertionError("Replay lineage did not include retryable failed previous attempt.")


def _same_idempotency_key(
    replay_request: Mapping[str, object],
    *,
    precondition_idempotency_key: str | None,
) -> bool | None:
    if precondition_idempotency_key is None:
        return None
    replay_key = _header_value(replay_request, "idempotency-key")
    if replay_key != precondition_idempotency_key:
        raise AssertionError("Replay used a different Idempotency-Key than the precondition.")
    return True


def _header_value(record: Mapping[str, object], key: str) -> object:
    headers = record.get("headers")
    if not isinstance(headers, dict):
        return None
    return headers.get(key)


def _matching_gets(
    response_records: Sequence[dict[str, object]],
    path: str,
) -> list[dict[str, object]]:
    return [
        record
        for record in response_records
        if record.get("method") == "GET"
        and record.get("path") == path
        and record.get("status") == 200
    ]


def _scrub_error(error: Mapping[str, object]) -> dict[str, object]:
    details = error.get("details")
    reason = details.get("reason") if isinstance(details, dict) else None
    return {
        "error_code": error.get("code"),
        "message": error.get("message"),
        "retryable": error.get("retryable") if isinstance(error.get("retryable"), bool) else None,
        "reason": reason,
    }


def _scrub_job(job: Mapping[str, object]) -> dict[str, object]:
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "source_format": job.get("source_format"),
        "output_format": job.get("output_format"),
        "phase": progress.get("phase") or progress.get("stage") or job.get("stage"),
        "processed_media_seconds": progress.get("audio_processed_media_seconds"),
        "total_media_seconds": progress.get("audio_total_media_seconds"),
        "percent_complete": progress.get("audio_percent_complete"),
        "pipeline_percent_complete": progress.get("audio_pipeline_percent_complete"),
    }


def _scrub_idempotency(idempotency: Mapping[str, object]) -> dict[str, object]:
    return {
        "state": idempotency.get("state"),
        "idempotent_replay": idempotency.get("idempotent_replay"),
        "active_job_id": idempotency.get("active_job_id"),
        "attempt_count": idempotency.get("attempt_count"),
        "current_attempt": idempotency.get("current_attempt"),
        "previous_attempts": idempotency.get("previous_attempts"),
        "replayed_job_id": idempotency.get("replayed_job_id"),
        "reattempt_of_job_id": idempotency.get("reattempt_of_job_id"),
    }


def _scrub_artifact(artifact: Mapping[str, object]) -> dict[str, object]:
    return {
        "artifact_key": artifact.get("artifact_key"),
        "availability": artifact.get("availability"),
        "content_type": artifact.get("content_type"),
        "size_bytes": artifact.get("size_bytes"),
        "retrieval_path_present": isinstance(artifact.get("retrieval_path"), str),
    }


def _scrub_result(result: Mapping[str, object]) -> dict[str, object]:
    artifact = result.get("artifact")
    return {
        "artifact": _scrub_artifact(artifact) if isinstance(artifact, dict) else None,
        "conversion_metadata": _scrub_conversion_metadata(result.get("conversion_metadata")),
    }


def _scrub_conversion_metadata(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {
        "pipeline_used": value.get("pipeline_used"),
        "backend_used": value.get("backend_used"),
        "acceleration_used": value.get("acceleration_used"),
    }
