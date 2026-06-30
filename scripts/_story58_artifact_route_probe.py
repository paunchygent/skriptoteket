"""Story 58 correction replay artifact route probe support.

Domain purpose:
    Observe immutable correction replay artifact sets through authenticated
    product/Gateway routes and bind those observations to safe correction
    request digests for Story 58 proof invariants.

Relationships:
    - Used by `scripts.playwright_pr_0337_correction_session_live` as helper
      logic for the canonical PR-0337 browser proof harness.
    - Complements `scripts._story58_artifact_set_invariants` by producing
      approved snapshot metadata without retaining response bytes or private
      correction/source material.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

from scripts._story58_artifact_set_invariants import record_story58_artifact_set_snapshot

REFERENCE_SCHEMA_VERSION = "correction_replay_artifact_reference_v1"
REQUIRED_REFERENCE_KEYS = (
    "artifact_key",
    "artifact_set_id",
    "content_sha256",
    "job_id",
)
SAFE_REQUEST_CONTEXT_KEYS = (
    "corrections_sha256",
    "job_id",
    "request_id",
    "source_bundle_id",
    "source_file_sha256",
    "source_state_sha256",
)


class Story58ArtifactRouteResponse(Protocol):
    """Response surface needed for Story 58 product-route observations."""

    @property
    def status(self) -> int: ...


class Story58ArtifactRouteRequestContext(Protocol):
    """Browser-authenticated request context for product-route probes."""

    def get(self, url: str, *, timeout: float | None = None) -> Story58ArtifactRouteResponse: ...


@dataclass(frozen=True)
class Story58CorrectionRequestContext:
    """Approved digest metadata for a correction apply request occurrence."""

    request_digest: str
    request_occurrence: int
    corrections_sha256: str | None = None
    job_id: str | None = None
    request_id: str | None = None
    source_bundle_id: str | None = None
    source_file_sha256: str | None = None
    source_state_sha256: str | None = None


def story58_latest_correction_request_context(
    summary: Mapping[str, object],
) -> Story58CorrectionRequestContext | None:
    """Return approved digest metadata for the latest correction apply request."""

    requests = summary.get("correction_apply_requests")
    if not isinstance(requests, list):
        return None
    for index in range(len(requests) - 1, -1, -1):
        request = requests[index]
        if not isinstance(request, dict):
            continue
        context = _request_context_from_summary(request, request_occurrence=index + 1)
        if context is not None:
            return context
    return None


def story58_snapshot_evidence_with_request_context(
    evidence: Mapping[str, object],
    context: Story58CorrectionRequestContext | None,
) -> dict[str, object]:
    """Attach approved correction request metadata to product-route evidence."""

    snapshot_evidence = dict(evidence)
    if context is None:
        return snapshot_evidence
    snapshot_evidence["request_digest"] = context.request_digest
    snapshot_evidence["request_occurrence"] = context.request_occurrence
    _copy_context_value(snapshot_evidence, "corrections_sha256", context.corrections_sha256)
    _copy_context_value(snapshot_evidence, "job_id", context.job_id)
    _copy_context_value(snapshot_evidence, "request_id", context.request_id)
    _copy_context_value(snapshot_evidence, "source_bundle_id", context.source_bundle_id)
    _copy_context_value(snapshot_evidence, "source_file_sha256", context.source_file_sha256)
    _copy_context_value(snapshot_evidence, "source_state_sha256", context.source_state_sha256)
    return snapshot_evidence


def probe_safe_correction_replay_artifacts(
    request_context: Story58ArtifactRouteRequestContext,
    *,
    api_base_url: str,
    summary: dict[str, object],
) -> dict[str, int]:
    """Probe retained safe correction replay references through product routes.

    Args:
        request_context: Authenticated Playwright browser request context.
        api_base_url: Protected product/Gateway API origin.
        summary: In-flight public proof manifest summary.

    Returns:
        Counts for attempted and skipped reference probes.

    Raises:
        AssertionError: If an attempted referenced artifact route is non-2xx.
    """

    attempted_count = 0
    skipped_count = 0
    for response_index, response in enumerate(
        _mapping_rows(summary.get("correction_apply_responses"))
    ):
        response_json = response.get("json")
        if not isinstance(response_json, dict):
            skipped_count += 1
            continue
        request_context_for_response = _request_context_for_response(
            summary,
            response_json=response_json,
            response_index=response_index,
        )
        references = _safe_reference_rows(
            response_json.get("correction_replay_artifact_references")
        )
        if not references:
            skipped_count += 1
            continue
        for reference in references:
            request = story58_artifact_reference_probe_request(reference)
            response_obj = request_context.get(
                f"{api_base_url.rstrip('/')}{request['path']}",
                timeout=30_000,
            )
            attempted_count += 1
            if response_obj.status < 200 or response_obj.status >= 300:
                raise AssertionError(
                    "Referenced correction replay artifact route returned "
                    f"HTTP {response_obj.status}: {request['path']}"
                )
            record_story58_artifact_set_snapshot(
                summary,
                story58_snapshot_evidence_with_request_context(
                    {
                        "artifact_key": request["artifact_key"],
                        "artifact_set_id": request["artifact_set_id"],
                        "content_sha256": request["content_sha256"],
                        "job_id": request["job_id"],
                        "path": request["path"],
                        "status": response_obj.status,
                    },
                    request_context_for_response,
                ),
                observed_via="apply-response-reference",
            )
    return {
        "attempted_count": attempted_count,
        "skipped_count": skipped_count,
    }


def story58_artifact_reference_probe_request(
    reference: Mapping[str, object],
) -> dict[str, str]:
    """Build a nested correction replay artifact request from a safe reference."""

    if reference.get("schema_version") != REFERENCE_SCHEMA_VERSION:
        raise AssertionError("Correction replay artifact reference schema is unsupported.")
    values: dict[str, str] = {}
    for key in REQUIRED_REFERENCE_KEYS:
        value = reference.get(key)
        if not isinstance(value, str) or not value:
            raise AssertionError(f"Correction replay artifact reference is missing {key}.")
        values[key] = value
    path = (
        f"/sir-convert/v2/convert/jobs/{quote(values['job_id'], safe='')}"
        f"/correction-replays/{quote(values['artifact_set_id'], safe='')}"
        f"/artifacts/{quote(values['artifact_key'], safe='')}"
        f"?content_sha256={quote(values['content_sha256'], safe='')}"
    )
    return {
        **values,
        "path": path,
    }


def _request_context_for_response(
    summary: Mapping[str, object],
    *,
    response_json: Mapping[str, object],
    response_index: int,
) -> Story58CorrectionRequestContext | None:
    requests = _mapping_rows(summary.get("correction_apply_requests"))
    response_request_id = response_json.get("request_id")
    if isinstance(response_request_id, str) and response_request_id:
        for index, request in enumerate(requests):
            if request.get("request_id") == response_request_id:
                return _request_context_from_summary(request, request_occurrence=index + 1)
    if response_index < len(requests):
        return _request_context_from_summary(
            requests[response_index],
            request_occurrence=response_index + 1,
        )
    return None


def _request_context_from_summary(
    request: Mapping[str, object],
    *,
    request_occurrence: int,
) -> Story58CorrectionRequestContext | None:
    request_digest = _first_string(
        request,
        ("body_sha256", "request_digest", "corrections_sha256"),
    )
    if request_digest is None:
        return None
    kwargs: dict[str, str] = {}
    for key in SAFE_REQUEST_CONTEXT_KEYS:
        value = request.get(key)
        if isinstance(value, str) and value:
            kwargs[key] = value
    return Story58CorrectionRequestContext(
        request_digest=request_digest,
        request_occurrence=request_occurrence,
        **kwargs,
    )


def _safe_reference_rows(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for reference in value:
        if not isinstance(reference, dict):
            continue
        if reference.get("schema_version") != REFERENCE_SCHEMA_VERSION:
            continue
        row: dict[str, str] = {"schema_version": REFERENCE_SCHEMA_VERSION}
        for key in REQUIRED_REFERENCE_KEYS:
            reference_value = reference.get(key)
            if isinstance(reference_value, str) and reference_value:
                row[key] = reference_value
        if all(key in row for key in REQUIRED_REFERENCE_KEYS):
            rows.append(row)
    return rows


def _mapping_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _copy_context_value(target: dict[str, object], key: str, value: str | None) -> None:
    if value:
        target[key] = value


def _first_string(payload: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None
