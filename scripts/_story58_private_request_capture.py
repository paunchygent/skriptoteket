"""Story 58 correction request private capture support.

Domain purpose:
    Capture raw Sir Convert correction request bodies for Story 58 closeout in
    an operator-provided private directory while retaining only safe metadata
    in public browser-proof manifests.

Relationships:
    - Used by `scripts.playwright_pr_0337_correction_session_live`.
    - Complements Sir Convert Story 58 proof artifacts without changing
      Skriptoteket product behavior or retained public artifact policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

SOURCE_STATE_ISSUE_PATH = "/sir-convert/v2/exam-authoring/corrections/source-state/issue"
CORRECTION_APPLY_PATH = "/sir-convert/v2/exam-authoring/corrections/apply"
TARGET_REQUEST_KINDS = {
    SOURCE_STATE_ISSUE_PATH: "source_state_issue",
    CORRECTION_APPLY_PATH: "correction_apply",
}
PRIVATE_MANIFEST_NAME = "manifest.json"


class _RequestLike(Protocol):
    """Playwright request surface required by the Story 58 capture helper."""

    @property
    def method(self) -> str: ...

    @property
    def post_data(self) -> bytes | str | None: ...

    @property
    def url(self) -> str: ...


@dataclass(frozen=True)
class _CapturedRequest:
    public_metadata: dict[str, object]
    private_manifest_entry: dict[str, object]


class Story58PrivateRequestCapture:
    """Capture Story 58 target request bodies outside retained artifacts."""

    def __init__(
        self,
        *,
        private_dir: Path,
        retained_artifact_dir: Path | None = None,
    ) -> None:
        self._private_dir = private_dir.expanduser().resolve()
        if retained_artifact_dir is not None:
            _assert_outside_retained_artifacts(
                private_dir=self._private_dir,
                retained_artifact_dir=retained_artifact_dir,
            )
        self._captures: list[_CapturedRequest] = []

    def handle_request(self, request: _RequestLike) -> None:
        """Capture one matching Playwright request if it is in Story 58 scope."""

        path = urlparse(request.url).path
        kind = TARGET_REQUEST_KINDS.get(path)
        if kind is None or request.method != "POST":
            return
        raw_body = _request_body_bytes(request)
        if raw_body is None:
            return

        self._private_dir.mkdir(parents=True, exist_ok=True)
        body_sha256 = hashlib.sha256(raw_body).hexdigest()
        sequence = len(self._captures) + 1
        filename = f"{sequence:03d}-{kind}-{body_sha256[:12]}.json"
        body_path = self._private_dir / filename
        body_path.write_bytes(raw_body)

        payload = _parse_json_object(raw_body)
        public_metadata = _public_metadata(
            kind=kind,
            method=request.method,
            path=path,
            body_sha256=body_sha256,
            payload=payload,
        )
        private_entry = {
            "body_sha256": body_sha256,
            "filename": filename,
            "kind": kind,
            "method": request.method,
            "path": path,
            "private_body_path": str(body_path),
        }
        self._captures.append(
            _CapturedRequest(
                public_metadata=public_metadata,
                private_manifest_entry=private_entry,
            )
        )
        self._write_private_manifest()

    def public_summary(self) -> dict[str, object]:
        """Return the Story 58-approved public manifest attachment."""

        return {
            "enabled": True,
            "private_capture_location": "private_capture_dir_only",
            "private_paths_retained": False,
            "raw_bodies_retained": False,
            "request_count": len(self._captures),
            "counts": {
                "correction_apply": self._count_kind("correction_apply"),
                "source_state_issue": self._count_kind("source_state_issue"),
            },
            "captures": [capture.public_metadata for capture in self._captures],
        }

    def attach_to_summary(self, summary: dict[str, object]) -> None:
        """Attach the redacted public capture summary to a proof manifest."""

        summary["story58_private_request_capture"] = self.public_summary()

    def _count_kind(self, kind: str) -> int:
        return sum(1 for capture in self._captures if capture.public_metadata.get("kind") == kind)

    def _write_private_manifest(self) -> None:
        manifest = {
            "captures": [capture.private_manifest_entry for capture in self._captures],
            "request_count": len(self._captures),
        }
        (self._private_dir / PRIVATE_MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _assert_outside_retained_artifacts(
    *,
    private_dir: Path,
    retained_artifact_dir: Path,
) -> None:
    retained_dir = retained_artifact_dir.expanduser().resolve()
    if private_dir == retained_dir or retained_dir in private_dir.parents:
        raise ValueError(
            "Story 58 private capture directory must not be inside the retained artifact directory."
        )


def _request_body_bytes(request: _RequestLike) -> bytes | None:
    raw_body = request.post_data
    if raw_body is None:
        return None
    if isinstance(raw_body, bytes):
        return raw_body
    if isinstance(raw_body, str):
        return raw_body.encode("utf-8")
    return None


def _parse_json_object(raw_body: bytes) -> dict[str, object]:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _public_metadata(
    *,
    kind: str,
    method: str,
    path: str,
    body_sha256: str,
    payload: dict[str, object],
) -> dict[str, object]:
    source_binding = _source_binding(payload)
    entry: dict[str, object] = {
        "body_sha256": body_sha256,
        "kind": kind,
        "method": method,
        "path": path,
    }
    _copy_string(entry, "schema_version", payload.get("schema_version"))
    _copy_string(entry, "request_id", payload.get("request_id"))
    _copy_string(entry, "job_id", _first_string(payload, ("job_id", "source_job_id")))
    _copy_string(
        entry,
        "source_bundle_id",
        _first_string(payload, ("source_bundle_id",), fallback=source_binding),
    )
    _copy_string(
        entry,
        "source_file_sha256",
        _first_string(payload, ("source_file_sha256",), fallback=source_binding),
    )
    _copy_string(
        entry,
        "source_state_sha256",
        _first_string(payload, ("source_state_sha256",), fallback=source_binding),
    )
    _copy_string(
        entry,
        "request_digest",
        _first_string(
            payload,
            ("request_digest", "request_sha256", "correction_request_sha256"),
        ),
    )
    _add_requested_target_metadata(entry, payload)
    _add_correction_metadata(entry, payload)
    _add_source_state_counts(entry, payload)
    return entry


def _source_binding(payload: dict[str, object]) -> dict[str, object]:
    source_binding = payload.get("source_binding")
    return source_binding if isinstance(source_binding, dict) else {}


def _first_string(
    payload: dict[str, object],
    keys: tuple[str, ...],
    *,
    fallback: dict[str, object] | None = None,
) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    if fallback is None:
        return None
    for key in keys:
        value = fallback.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _copy_string(entry: dict[str, object], key: str, value: object) -> None:
    if isinstance(value, str) and value:
        entry[key] = value


def _add_requested_target_metadata(entry: dict[str, object], payload: dict[str, object]) -> None:
    requested_targets = payload.get("requested_targets")
    if not isinstance(requested_targets, list):
        return
    safe_targets = [target for target in requested_targets if isinstance(target, str)]
    entry["requested_target_count"] = len(safe_targets)
    if safe_targets:
        entry["requested_targets"] = safe_targets


def _add_correction_metadata(entry: dict[str, object], payload: dict[str, object]) -> None:
    corrections = payload.get("corrections")
    if not isinstance(corrections, list):
        return
    entry["correction_count"] = len(corrections)
    entry["corrections_sha256"] = hashlib.sha256(
        json.dumps(corrections, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _add_source_state_counts(entry: dict[str, object], payload: dict[str, object]) -> None:
    source_state = payload.get("source_authoring_state")
    if not isinstance(source_state, dict):
        source_state = payload.get("source_state")
    if not isinstance(source_state, dict):
        return
    items = source_state.get("items")
    if isinstance(items, list):
        entry["source_state_item_count"] = len(items)
