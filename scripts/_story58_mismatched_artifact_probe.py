"""Story 58 correction replay artifact mismatch proof support.

Domain purpose:
    Build and verify a fail-closed nested correction replay artifact request
    by corrupting only the retained content hash of a real replay artifact
    URL, while exposing only Story 58-approved public evidence metadata.

Relationships:
    - Used by `scripts.playwright_pr_0337_correction_session_live`.
    - Complements `scripts._story58_private_request_capture` by proving the
      nested artifact route rejects mismatched replay references.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

CORRECTION_REPLAY_ARTIFACT_REFERENCE_SCHEMA = "correction_replay_artifact_reference_v1"
CORRECTION_REPLAY_REFERENCE_SAFE_KEYS = (
    "schema_version",
    "artifact_set_id",
    "artifact_key",
    "content_sha256",
    "request_id",
    "source_binding_digest",
    "source_state_sha256",
    "correction_payload_digest",
    "target_set_digest",
)
MISMATCHED_ARTIFACT_DOWNLOAD_ALLOWED_ERRORS = {
    (404, "correction_replay_artifact_set_not_found"),
    (409, "correction_replay_artifact_reference_mismatch"),
}


class Story58ProbeResponse(Protocol):
    """Response surface needed for redacted mismatch probe summaries."""

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def status(self) -> int: ...

    def json(self) -> object: ...


class Story58RequestContext(Protocol):
    """Browser-authenticated request context used by the mismatch probe."""

    def get(self, url: str, *, timeout: float | None = None) -> Story58ProbeResponse: ...


def safe_correction_replay_artifact_references(
    payload: Mapping[str, object],
) -> list[dict[str, str]]:
    """Return only approved correction replay artifact reference metadata."""

    references = payload.get("correction_replay_artifact_references")
    if not isinstance(references, list):
        return []
    safe_references: list[dict[str, str]] = []
    for reference in references:
        if not isinstance(reference, dict):
            continue
        if reference.get("schema_version") != CORRECTION_REPLAY_ARTIFACT_REFERENCE_SCHEMA:
            continue
        safe_reference: dict[str, str] = {}
        for key in CORRECTION_REPLAY_REFERENCE_SAFE_KEYS:
            value = reference.get(key)
            if isinstance(value, str) and value:
                safe_reference[key] = value
        if safe_reference:
            safe_references.append(safe_reference)
    return safe_references


def mismatched_artifact_download_request(evidence: Mapping[str, object]) -> dict[str, str]:
    """Build a nested replay artifact request with only the content hash changed."""

    path = evidence.get("path")
    original_content_sha256 = evidence.get("content_sha256")
    artifact_set_id = evidence.get("replay_artifact_set_id")
    artifact_key = evidence.get("replay_artifact_key")
    if not all(
        isinstance(value, str) and value
        for value in (path, original_content_sha256, artifact_set_id, artifact_key)
    ):
        raise AssertionError("Replay artifact evidence is missing mismatch probe authority.")
    parsed = urlparse(str(path))
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    content_hash_indexes = [
        index for index, (key, _value) in enumerate(query_pairs) if key == "content_sha256"
    ]
    if len(content_hash_indexes) != 1:
        raise AssertionError("Replay artifact path must include exactly one content_sha256 query.")
    mismatched_content_sha256 = _mismatched_content_sha256(str(original_content_sha256))
    query_pairs[content_hash_indexes[0]] = ("content_sha256", mismatched_content_sha256)
    mismatched_path = urlunparse(("", "", parsed.path, "", urlencode(query_pairs), ""))
    return {
        "artifact_key": str(artifact_key),
        "artifact_set_id": str(artifact_set_id),
        "mismatched_content_sha256": mismatched_content_sha256,
        "original_content_sha256": str(original_content_sha256),
        "path": mismatched_path,
    }


def mismatched_artifact_download_probe_summary(
    response: Story58ProbeResponse,
    *,
    request: Mapping[str, str],
) -> dict[str, object]:
    """Summarize a mismatch probe without retaining response body details."""

    entry: dict[str, object] = {
        "artifact_key": request["artifact_key"],
        "artifact_set_id": request["artifact_set_id"],
        "mismatched_content_sha256": request["mismatched_content_sha256"],
        "original_content_sha256": request["original_content_sha256"],
        "path": request["path"],
        "status": response.status,
    }
    content_type = response.headers.get("content-type") or ""
    if "application/json" not in content_type:
        return entry
    try:
        payload = response.json()
    except Exception:  # pragma: no cover - diagnostic evidence only.
        return entry
    error_code = _json_error_code(payload)
    if error_code is not None:
        entry["error_code"] = error_code
    return entry


def assert_mismatched_artifact_probe_fail_closed(entry: Mapping[str, object]) -> None:
    """Assert the nested artifact route rejected the mismatched reference."""

    observed = (entry.get("status"), entry.get("error_code"))
    if observed in MISMATCHED_ARTIFACT_DOWNLOAD_ALLOWED_ERRORS:
        return
    raise AssertionError(
        "Mismatched correction replay artifact download did not fail closed: "
        f"HTTP {entry.get('status')} error_code={entry.get('error_code')!r}."
    )


def probe_mismatched_replay_artifact_download(
    request_context: Story58RequestContext,
    *,
    api_base_url: str,
    artifact_download: Mapping[str, object],
) -> dict[str, object]:
    """Issue an authenticated mismatch probe through the browser request context."""

    request = mismatched_artifact_download_request(artifact_download)
    response = request_context.get(f"{api_base_url}{request['path']}", timeout=30_000)
    entry = mismatched_artifact_download_probe_summary(response, request=request)
    assert_mismatched_artifact_probe_fail_closed(entry)
    return entry


def _mismatched_content_sha256(content_sha256: str) -> str:
    prefix = "sha256:" if content_sha256.startswith("sha256:") else ""
    digest = content_sha256.removeprefix(prefix)
    if not digest:
        raise AssertionError("Replay artifact content_sha256 is empty.")
    replacement = "1" if digest[0] == "0" else "0"
    return f"{prefix}{replacement}{digest[1:]}"


def _json_error_code(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("code"), str):
        return error["code"]
    if isinstance(error, str):
        return error
    for key in ("error_code", "code"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None
