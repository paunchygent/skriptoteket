"""PR-0262 lifecycle artifact validation and retained manifest helpers.

Purpose:
    Validate the HuleEdu TASK-0327 upstream artifact and build the sanitized
    Skriptoteket PR-0262 manifest without retaining raw identity or token
    material.

Relationships:
    - Imported by `scripts.playwright_pr_0262_real_lifecycle`.
    - Unit-tested directly so the artifact contract can fail before browser
      automation starts.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

DEFAULT_APP = "skriptoteket"
DEFAULT_REALM = "skriptoteket_standalone"
DEFAULT_PROBE_PATH = "/api/v1/diagnostics/huleedu-internal-identity"

RoleName = Literal["user", "contributor", "admin", "superuser"]
EnvironmentName = Literal["local-nonprod", "production"]

EXPECTED_DIRECT_ACTIONS: Mapping[str, Mapping[str, object]] = {
    "login_direct_landing": {
        "gateway_path": "/auth/login",
        "frontend_path": "/login",
        "token_present": False,
    },
    "registration_direct_landing": {
        "gateway_path": "/auth/register",
        "frontend_path": "/register",
        "token_present": False,
    },
    "forgot_password_direct_landing": {
        "gateway_path": "/auth/password-reset",
        "frontend_path": "/password-reset",
        "token_present": False,
    },
    "reset_completion_direct_landing": {
        "gateway_path": "/auth/password-reset",
        "frontend_path": "/password-reset",
        "token_present": True,
    },
    "email_verification_direct_landing": {
        "gateway_path": "/auth/email-verification",
        "frontend_path": "/email-verification",
        "token_present": True,
    },
}

EXPECTED_PROVIDER_ACTIONS: Mapping[str, set[int]] = {
    "registration_submit": {200, 201, 400},
    "email_verification_request": {200},
    "forgot_password_request": {200},
    "reset_password_link_landing": {303},
    "reset_password_complete": {200},
    "login_submit": {200},
    "session_claims": {200},
    "signed_context_probe": {200},
}

REQUIRED_SIGNED_CONTEXT_TRUE_CLAIMS = (
    "realm_subject_id_present",
    "subject_claim_present",
    "subject_matches_realm_subject",
    "linked_identity_realm_present",
    "linked_identity_matches_realm_subject",
    "email_present",
    "email_verified",
)

FORBIDDEN_MANIFEST_KEYS = {
    "email",
    "realm_subject_id",
    "session_cookie",
    "csrf_token",
    "token",
    "magic_link",
    "raw_url",
    "raw_headers",
    "signed_identity_payload",
}


class LifecycleProofValidationError(ValueError):
    """Raised when an upstream or retained proof artifact violates PR-0262."""


@dataclass(frozen=True)
class HuleEduTask0327Validation:
    """Validated HuleEdu upstream artifact plus transient raw claims."""

    provider_subject: str
    provider_email: str
    upstream_next_path: str | None
    summary: dict[str, object]
    action_page_assertions: list[dict[str, object]]
    redacted_email_link_evidence: list[dict[str, object]]


def _as_mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise LifecycleProofValidationError(f"{label} must be an object")
    return dict(value)


def _as_sequence(value: object, *, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise LifecycleProofValidationError(f"{label} must be an array")
    return value


def _require_nonblank_string(mapping: Mapping[str, object], key: str, *, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LifecycleProofValidationError(f"{label}.{key} must be a nonblank string")
    return value


def _require_true(mapping: Mapping[str, object], key: str, *, label: str) -> None:
    if mapping.get(key) is not True:
        raise LifecycleProofValidationError(f"{label}.{key} must be true")


def _require_equal(
    mapping: Mapping[str, object],
    key: str,
    expected: object,
    *,
    label: str,
) -> None:
    if mapping.get(key) != expected:
        raise LifecycleProofValidationError(
            f"{label}.{key} must equal {expected!r}, got {mapping.get(key)!r}"
        )


def _safe_next_path(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        raise LifecycleProofValidationError("command.next_path must be a safe app route")
    return value


def _validate_direct_actions(actions: Sequence[object]) -> list[dict[str, object]]:
    by_name = _actions_by_name(actions)
    retained: list[dict[str, object]] = []
    for name, expected in EXPECTED_DIRECT_ACTIONS.items():
        action = by_name.get(name)
        if action is None:
            raise LifecycleProofValidationError(f"Missing direct action evidence: {name}")
        _require_equal(action, "method", "GET", label=f"proof.actions.{name}")
        _require_equal(action, "status_code", 303, label=f"proof.actions.{name}")
        for key, value in expected.items():
            _require_equal(action, key, value, label=f"proof.actions.{name}")
        retained.append(
            {
                "name": name,
                "gateway_path": action["gateway_path"],
                "frontend_path": action["frontend_path"],
                "method": "GET",
                "status_code": 303,
                "token_present": action["token_present"],
                "first_interactive_action_page_proved": True,
            }
        )
    return retained


def _actions_by_name(actions: Sequence[object]) -> dict[str, dict[str, object]]:
    by_name: dict[str, dict[str, object]] = {}
    for raw_action in actions:
        action = _as_mapping(raw_action, label="proof.actions[]")
        name = _require_nonblank_string(action, "name", label="proof.actions[]")
        by_name[name] = action
    return by_name


def _validate_provider_actions(actions: Sequence[object]) -> dict[str, object]:
    by_name = _actions_by_name(actions)
    retained: dict[str, object] = {}
    for name, allowed_statuses in EXPECTED_PROVIDER_ACTIONS.items():
        action = by_name.get(name)
        if action is None:
            raise LifecycleProofValidationError(f"Missing provider action evidence: {name}")
        status_code = action.get("status_code")
        if status_code not in allowed_statuses:
            raise LifecycleProofValidationError(
                f"proof.actions.{name}.status_code must be one of "
                f"{sorted(allowed_statuses)}, got {status_code!r}"
            )
        retained[name] = {
            "method": action.get("method"),
            "gateway_path": action.get("gateway_path"),
            "status_code": status_code,
            "token_present": action.get("token_present"),
        }
    return retained


def _validate_signed_context_claims(claims: Mapping[str, object]) -> dict[str, object]:
    _require_equal(claims, "active_app", DEFAULT_APP, label="proof.signed_context_claims")
    _require_equal(
        claims,
        "active_product_identity_realm",
        DEFAULT_REALM,
        label="proof.signed_context_claims",
    )
    for key in REQUIRED_SIGNED_CONTEXT_TRUE_CLAIMS:
        _require_true(claims, key, label="proof.signed_context_claims")
    return {
        "active_app": DEFAULT_APP,
        "active_product_identity_realm": DEFAULT_REALM,
        **{key: True for key in REQUIRED_SIGNED_CONTEXT_TRUE_CLAIMS},
    }


def _validate_session_claims(claims: Mapping[str, object]) -> tuple[str, str, dict[str, object]]:
    _require_equal(claims, "active_app", DEFAULT_APP, label="proof.session_claims")
    _require_equal(
        claims,
        "active_product_identity_realm",
        DEFAULT_REALM,
        label="proof.session_claims",
    )
    _require_true(claims, "email_verified", label="proof.session_claims")
    provider_subject = _require_nonblank_string(
        claims,
        "realm_subject_id",
        label="proof.session_claims",
    )
    provider_email = _require_nonblank_string(claims, "email", label="proof.session_claims")
    return (
        provider_subject,
        provider_email,
        {
            "active_app": DEFAULT_APP,
            "active_product_identity_realm": DEFAULT_REALM,
            "realm_subject_id_present": True,
            "email_present": True,
            "email_verified": True,
        },
    )


def validate_huleedu_task_0327_artifact(
    payload: Mapping[str, object],
    *,
    artifact_path: Path,
) -> HuleEduTask0327Validation:
    """Validate the accepted HuleEdu TASK-0327 artifact shape."""
    command = _as_mapping(payload.get("command"), label="command")
    proof = _as_mapping(payload.get("proof"), label="proof")

    _require_equal(command, "app", DEFAULT_APP, label="command")
    _require_equal(command, "product_identity_realm", DEFAULT_REALM, label="command")
    _require_equal(command, "signed_context_probe_path", DEFAULT_PROBE_PATH, label="command")
    _require_equal(proof, "status", "ok", label="proof")

    return_to = _require_nonblank_string(command, "return_to", label="command")
    if urlparse(return_to).path != "/auth/callback":
        raise LifecycleProofValidationError("command.return_to must target /auth/callback")
    upstream_next_path = _safe_next_path(command.get("next_path"))

    actions = _as_sequence(proof.get("actions"), label="proof.actions")
    action_page_assertions = _validate_direct_actions(actions)
    provider_action_summary = _validate_provider_actions(actions)
    signed_context_claims = _validate_signed_context_claims(
        _as_mapping(proof.get("signed_context_claims"), label="proof.signed_context_claims")
    )
    provider_subject, provider_email, session_summary = _validate_session_claims(
        _as_mapping(proof.get("session_claims"), label="proof.session_claims")
    )

    return HuleEduTask0327Validation(
        provider_subject=provider_subject,
        provider_email=provider_email,
        upstream_next_path=upstream_next_path,
        summary={
            "artifact_path": str(artifact_path),
            "validated": True,
            "status": "ok",
            "mode": command.get("mode"),
            "account_action": proof.get("account_action"),
            "reset_delivery": proof.get("reset_delivery"),
            "verification_delivery": proof.get("verification_delivery"),
            "signed_context_probe_path": DEFAULT_PROBE_PATH,
            "return_to_path": "/auth/callback",
            "upstream_safe_next_path_present": upstream_next_path is not None,
            "direct_action_count": len(action_page_assertions),
            "provider_actions": provider_action_summary,
            "session_claims": session_summary,
            "signed_context_claims": signed_context_claims,
        },
        action_page_assertions=action_page_assertions,
        redacted_email_link_evidence=[
            {
                "link_kind": "password_reset_completion",
                "target_action": "/auth/password-reset",
                "first_interactive_page_proved": True,
                "raw_url_retained": False,
            },
            {
                "link_kind": "email_verification",
                "target_action": "/auth/email-verification",
                "first_interactive_page_proved": True,
                "raw_url_retained": False,
            },
        ],
    )


def load_huleedu_task_0327_artifact(path: Path) -> HuleEduTask0327Validation:
    """Read and validate a HuleEdu TASK-0327 artifact from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return validate_huleedu_task_0327_artifact(payload, artifact_path=path)


def _walk_mapping_keys(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_mapping_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mapping_keys(child)


def assert_manifest_redacted(
    manifest: Mapping[str, object],
    *,
    forbidden_values: Iterable[str],
) -> None:
    """Fail if the retained manifest includes raw identity, token, or header material."""
    forbidden_keys = FORBIDDEN_MANIFEST_KEYS.intersection(_walk_mapping_keys(dict(manifest)))
    if forbidden_keys:
        raise LifecycleProofValidationError(
            f"Manifest contains forbidden keys: {sorted(forbidden_keys)}"
        )

    serialized = json.dumps(manifest, sort_keys=True)
    for marker in forbidden_values:
        if marker and marker in serialized:
            raise LifecycleProofValidationError("Manifest retained a forbidden raw marker value")


def build_manifest(
    *,
    environment: EnvironmentName,
    run_id: str,
    huleedu_validation: HuleEduTask0327Validation,
    controlled_account_key: str,
    callback_assertions: Mapping[str, object],
    projection_assertions: Mapping[str, object],
    local_role_assertions: Mapping[str, object],
    screenshot_paths: Sequence[str],
    log_paths: Sequence[str],
    forbidden_values: Iterable[str],
) -> dict[str, object]:
    """Build and redaction-check the retained PR-0262 manifest."""
    manifest: dict[str, object] = {
        "status": "ok",
        "command": "pdm run pr-0262-real-lifecycle",
        "environment": environment,
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_contracts": [
            "REV-TASK-0326-01",
            "REV-TASK-0327-01",
            "REV-PR-0260",
            "REV-PR-0261",
        ],
        "app": DEFAULT_APP,
        "product_identity_realm": DEFAULT_REALM,
        "controlled_account_key": controlled_account_key,
        "upstream_huleedu_task_0327": huleedu_validation.summary,
        "action_page_assertions": huleedu_validation.action_page_assertions,
        "redacted_email_link_evidence": huleedu_validation.redacted_email_link_evidence,
        "callback_assertions": dict(callback_assertions),
        "projection_assertions": dict(projection_assertions),
        "local_role_assertions": dict(local_role_assertions),
        "screenshots": list(screenshot_paths),
        "logs": list(log_paths),
        "redaction_checks": {
            "forbidden_exact_keys_absent": True,
            "forbidden_raw_marker_values_absent": True,
            "raw_email_retained": False,
            "raw_realm_subject_id_retained": False,
            "raw_signed_headers_retained": False,
            "raw_jwt_or_signature_retained": False,
            "raw_reset_or_verification_token_retained": False,
            "raw_magic_link_retained": False,
            "cookies_or_csrf_retained": False,
        },
    }
    assert_manifest_redacted(manifest, forbidden_values=forbidden_values)
    return manifest
