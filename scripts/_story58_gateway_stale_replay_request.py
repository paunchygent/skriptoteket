"""Story 58 Gateway stale-replay request contract.

Domain purpose:
    Build the deterministic Sir Convert create-job request and replay
    fingerprints used by the authenticated Story 58 Gateway proof.

Relationships:
    Used by `scripts.story58_gateway_stale_replay_proof` to keep request
    construction, source hashing, and owner-scope digest semantics out of the
    browser runner.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

DEFAULT_TARGETS = ("examnet_pdf", "qti_package")


def build_story58_gateway_job_spec(
    filename: str,
    *,
    targets: Sequence[str] = DEFAULT_TARGETS,
) -> dict[str, object]:
    """Build the stable Sir Convert job spec for Story 58 stale replay."""
    return {
        "api_version": "v2",
        "source": {
            "kind": "upload",
            "filename": filename,
            "format": "digiexam_dxe",
        },
        "conversion": {
            "output_format": "examnet_migration_bundle",
            "targets": list(targets),
            "artifact_language": "sv",
            "reference_docx_filename": None,
        },
        "digiexam_migration_options": {
            "completion_mode": "local_llm_suggest_missing_machine_marked",
            "remote_provider_policy": "forbidden",
            "result_pdf_usage": "correct_machine_marked_answers_only",
            "manual_follow_up_policy": "emit_item_addressable_report",
        },
        "retention": {
            "pin": False,
        },
    }


def stable_story58_gateway_json(payload: Mapping[str, object]) -> str:
    """Serialize replay request JSON exactly as the fingerprint expects."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def story58_sha256_bytes(payload: bytes) -> str:
    """Return the lowercase SHA-256 hex digest for retained proof fingerprints."""
    return hashlib.sha256(payload).hexdigest()


def story58_request_fingerprint(*, job_spec_json: str, file_sha256: str) -> str:
    """Compute the Sir Convert stale-record request fingerprint."""
    return story58_sha256_bytes(f"{job_spec_json}:{file_sha256}:::::".encode("utf-8"))


def story58_scope_digest(*, owner_scope: str, idempotency_key: str) -> str:
    """Compute the owner-scoped idempotency digest for the Gateway replay."""
    scope_key = f"{owner_scope}:POST:/v2/convert/jobs:{idempotency_key}"
    return story58_sha256_bytes(scope_key.encode("utf-8"))
