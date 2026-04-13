"""PR-0254 artifact preflight and redacted manifest helpers.

Purpose:
    Validate retained upstream auth-cutover proof artifacts and build the final
    PR-0254 manifest without retaining raw identity, token, cookie, CSRF, URL,
    or signed-context material.

Relationships:
    - Imported by `scripts.playwright_pr_0254_auth_cutover`.
    - Reuses the accepted PR-0262 HuleEdu TASK-0327 validator for provider
      lifecycle evidence.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from scripts._pr_0262_lifecycle_manifest import (
    LifecycleProofValidationError,
    validate_huleedu_task_0327_artifact,
)

DEFAULT_APP = "skriptoteket"
DEFAULT_REALM = "skriptoteket_standalone"
EnvironmentName = Literal["local-nonprod", "production"]

FORBIDDEN_FINAL_KEYS = {
    "body_prefix",
    "cookie",
    "cookies",
    "csrf_token",
    "email",
    "final_url",
    "href",
    "jwt",
    "magic_link",
    "raw_headers",
    "raw_url",
    "realm_subject_id",
    "session_cookie",
    "signed_headers",
    "signed_identity_payload",
    "signature",
    "token",
    "url",
}


class AuthCutoverManifestError(ValueError):
    """Raised when PR-0254 preflight or redaction validation fails."""


@dataclass(frozen=True)
class ArtifactValidation:
    """Sanitized validation summary for one prerequisite artifact."""

    status: str
    validated: bool
    artifact_path: str
    summary: dict[str, object]


def load_json_artifact(path: Path) -> dict[str, object]:
    """Load a JSON artifact and fail with a useful preflight error."""
    if not path.exists():
        raise AuthCutoverManifestError(f"Required artifact does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthCutoverManifestError(f"Artifact is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise AuthCutoverManifestError(f"Artifact must be a JSON object: {path}")
    return payload


def _as_mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AuthCutoverManifestError(f"{label} must be an object")
    return dict(value)


def _as_sequence(value: object, *, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise AuthCutoverManifestError(f"{label} must be an array")
    return value


def _require_equal(
    mapping: Mapping[str, object], key: str, expected: object, *, label: str
) -> None:
    if mapping.get(key) != expected:
        raise AuthCutoverManifestError(
            f"{label}.{key} must equal {expected!r}, got {mapping.get(key)!r}"
        )


def _require_true(mapping: Mapping[str, object], key: str, *, label: str) -> None:
    if mapping.get(key) is not True:
        raise AuthCutoverManifestError(f"{label}.{key} must be true")


def _require_false(mapping: Mapping[str, object], key: str, *, label: str) -> None:
    if mapping.get(key) is not False:
        raise AuthCutoverManifestError(f"{label}.{key} must be false")


def _require_nonblank_string(mapping: Mapping[str, object], key: str, *, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AuthCutoverManifestError(f"{label}.{key} must be a nonblank string")
    return value


def _walk_mapping_keys(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_mapping_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mapping_keys(child)


def assert_final_manifest_redacted(
    manifest: Mapping[str, object],
    *,
    forbidden_values: Iterable[str],
) -> None:
    """Fail if the PR-0254 manifest retained forbidden keys or raw values."""
    forbidden_keys = FORBIDDEN_FINAL_KEYS.intersection(_walk_mapping_keys(dict(manifest)))
    if forbidden_keys:
        raise AuthCutoverManifestError(
            f"Manifest contains forbidden retained keys: {sorted(forbidden_keys)}"
        )

    serialized = json.dumps(manifest, sort_keys=True)
    for marker in forbidden_values:
        if marker and marker in serialized:
            raise AuthCutoverManifestError("Manifest retained a forbidden raw marker value")


def _validate_common_retained_manifest(
    payload: Mapping[str, object],
    *,
    label: str,
) -> None:
    _require_equal(payload, "status", "ok", label=label)
    _require_equal(payload, "app", DEFAULT_APP, label=label)
    _require_equal(payload, "product_identity_realm", DEFAULT_REALM, label=label)


def _assert_redaction_flags_false(
    payload: Mapping[str, object],
    *,
    label: str,
    flags: Sequence[str],
) -> None:
    checks = _as_mapping(payload.get("redaction_checks"), label=f"{label}.redaction_checks")
    for flag in flags:
        _require_false(checks, flag, label=f"{label}.redaction_checks")


def validate_pr_0261_manifest(
    payload: Mapping[str, object], *, artifact_path: Path
) -> ArtifactValidation:
    """Validate the retained PR-0261 auth action/probe manifest."""
    _validate_common_retained_manifest(payload, label="pr_0261")
    _assert_redaction_flags_false(
        payload,
        label="pr_0261",
        flags=(
            "raw_tokens_retained",
            "raw_signed_context_retained",
            "raw_session_material_retained",
        ),
    )
    actions = _as_sequence(payload.get("actions"), label="pr_0261.actions")
    if len(actions) < 5:
        raise AuthCutoverManifestError("pr_0261.actions must include direct action coverage")

    action_names: list[str] = []
    for index, raw_action in enumerate(actions):
        action = _as_mapping(raw_action, label=f"pr_0261.actions[{index}]")
        action_names.append(
            _require_nonblank_string(action, "name", label=f"pr_0261.actions[{index}]")
        )
        provider = _as_mapping(action.get("provider"), label=f"pr_0261.actions[{index}].provider")
        _require_equal(provider, "app", DEFAULT_APP, label=f"pr_0261.actions[{index}].provider")
        _require_equal(
            provider,
            "product_identity_realm",
            DEFAULT_REALM,
            label=f"pr_0261.actions[{index}].provider",
        )

    probe = _as_mapping(payload.get("consumer_probe"), label="pr_0261.consumer_probe")
    _require_equal(probe, "status", "ok", label="pr_0261.consumer_probe")
    claims = _as_mapping(probe.get("claims"), label="pr_0261.consumer_probe.claims")
    _require_equal(claims, "active_app", DEFAULT_APP, label="pr_0261.consumer_probe.claims")
    _require_equal(
        claims,
        "active_product_identity_realm",
        DEFAULT_REALM,
        label="pr_0261.consumer_probe.claims",
    )

    return ArtifactValidation(
        status="ok",
        validated=True,
        artifact_path=str(artifact_path),
        summary={
            "status": "ok",
            "validated": True,
            "artifact_path": str(artifact_path),
            "direct_action_count": len(actions),
            "action_names": action_names,
            "consumer_probe_status": "ok",
            "redacted": True,
        },
    )


def validate_pr_0262_manifest(
    payload: Mapping[str, object], *, artifact_path: Path
) -> ArtifactValidation:
    """Validate the retained PR-0262 lifecycle/projection/role manifest."""
    _validate_common_retained_manifest(payload, label="pr_0262")
    checks = _as_mapping(payload.get("redaction_checks"), label="pr_0262.redaction_checks")
    for flag in (
        "raw_email_retained",
        "raw_realm_subject_id_retained",
        "raw_signed_headers_retained",
        "raw_jwt_or_signature_retained",
        "raw_reset_or_verification_token_retained",
        "raw_magic_link_retained",
        "cookies_or_csrf_retained",
    ):
        _require_false(checks, flag, label="pr_0262.redaction_checks")
    _require_true(checks, "forbidden_exact_keys_absent", label="pr_0262.redaction_checks")
    _require_true(checks, "forbidden_raw_marker_values_absent", label="pr_0262.redaction_checks")

    upstream = _as_mapping(
        payload.get("upstream_huleedu_task_0327"),
        label="pr_0262.upstream_huleedu_task_0327",
    )
    _require_equal(upstream, "status", "ok", label="pr_0262.upstream_huleedu_task_0327")
    _require_true(upstream, "validated", label="pr_0262.upstream_huleedu_task_0327")
    role = _as_mapping(payload.get("local_role_assertions"), label="pr_0262.local_role_assertions")
    _require_true(role, "role_matches_expected", label="pr_0262.local_role_assertions")

    return ArtifactValidation(
        status="ok",
        validated=True,
        artifact_path=str(artifact_path),
        summary={
            "status": "ok",
            "validated": True,
            "artifact_path": str(artifact_path),
            "environment": payload.get("environment"),
            "upstream_huleedu_task_0327": {
                "status": "ok",
                "validated": True,
            },
            "expected_local_role": role.get("expected_local_role"),
            "observed_local_role": role.get("observed_local_role"),
            "role_matches_expected": True,
            "redacted": True,
        },
    )


def validate_huleedu_task_0326_artifact(
    payload: Mapping[str, object],
    *,
    artifact_path: Path,
) -> ArtifactValidation:
    """Validate HuleEdu TASK-0326 subject export proof without retaining subjects."""
    _require_equal(payload, "status", "ok", label="huleedu_task_0326")
    export = _as_mapping(payload.get("export"), label="huleedu_task_0326.export")
    _require_equal(export, "active_app", DEFAULT_APP, label="huleedu_task_0326.export")
    _require_equal(
        export,
        "active_product_identity_realm",
        DEFAULT_REALM,
        label="huleedu_task_0326.export",
    )
    accounts = _as_sequence(export.get("accounts"), label="huleedu_task_0326.export.accounts")
    if not accounts:
        raise AuthCutoverManifestError("huleedu_task_0326.export.accounts must not be empty")

    role_hints: set[str] = set()
    stable_account_keys: list[str] = []
    for index, raw_account in enumerate(accounts):
        account = _as_mapping(raw_account, label=f"huleedu_task_0326.export.accounts[{index}]")
        _require_equal(
            account,
            "active_app",
            DEFAULT_APP,
            label=f"huleedu_task_0326.export.accounts[{index}]",
        )
        _require_equal(
            account,
            "active_product_identity_realm",
            DEFAULT_REALM,
            label=f"huleedu_task_0326.export.accounts[{index}]",
        )
        _require_true(
            account,
            "email_verified",
            label=f"huleedu_task_0326.export.accounts[{index}]",
        )
        stable_account_keys.append(
            _require_nonblank_string(
                account,
                "stable_account_key",
                label=f"huleedu_task_0326.export.accounts[{index}]",
            )
        )
        role_hints.add(
            _require_nonblank_string(
                account,
                "skriptoteket_role_hint",
                label=f"huleedu_task_0326.export.accounts[{index}]",
            )
        )
        _require_nonblank_string(
            account,
            "realm_subject_id",
            label=f"huleedu_task_0326.export.accounts[{index}]",
        )

    return ArtifactValidation(
        status="ok",
        validated=True,
        artifact_path=str(artifact_path),
        summary={
            "status": "ok",
            "validated": True,
            "artifact_path": str(artifact_path),
            "schema_version": export.get("schema_version"),
            "account_count": len(accounts),
            "stable_account_keys": stable_account_keys,
            "role_hints": sorted(role_hints),
            "app": DEFAULT_APP,
            "product_identity_realm": DEFAULT_REALM,
            "raw_subject_export_material_not_retained": True,
        },
    )


def validate_huleedu_task_0327_manifest(
    payload: Mapping[str, object],
    *,
    artifact_path: Path,
) -> ArtifactValidation:
    """Validate HuleEdu TASK-0327 lifecycle proof and retain only its summary."""
    try:
        validation = validate_huleedu_task_0327_artifact(payload, artifact_path=artifact_path)
    except LifecycleProofValidationError as exc:
        raise AuthCutoverManifestError(str(exc)) from exc

    return ArtifactValidation(
        status="ok",
        validated=True,
        artifact_path=str(artifact_path),
        summary={
            **validation.summary,
            "artifact_path": str(artifact_path),
            "redacted_summary_only": True,
        },
    )


def validate_prerequisite_artifacts(
    *,
    huleedu_task_0326_path: Path,
    huleedu_task_0327_path: Path,
    pr_0261_path: Path,
    pr_0262_path: Path,
) -> dict[str, dict[str, object]]:
    """Validate all PR-0254 prerequisite artifacts and return sanitized summaries."""
    validations = {
        "huleedu_task_0326": validate_huleedu_task_0326_artifact(
            load_json_artifact(huleedu_task_0326_path),
            artifact_path=huleedu_task_0326_path,
        ),
        "huleedu_task_0327": validate_huleedu_task_0327_manifest(
            load_json_artifact(huleedu_task_0327_path),
            artifact_path=huleedu_task_0327_path,
        ),
        "pr_0261": validate_pr_0261_manifest(
            load_json_artifact(pr_0261_path),
            artifact_path=pr_0261_path,
        ),
        "pr_0262": validate_pr_0262_manifest(
            load_json_artifact(pr_0262_path),
            artifact_path=pr_0262_path,
        ),
    }
    return {
        name: {
            "status": validation.status,
            "validated": validation.validated,
            **validation.summary,
        }
        for name, validation in validations.items()
    }


def build_manifest(
    *,
    environment: EnvironmentName,
    run_id: str,
    command: str,
    validated_prerequisite_artifacts: Mapping[str, object],
    public_route_assertions: Mapping[str, object],
    auth_entry_assertions: Mapping[str, object],
    gateway_proxy_assertions: Mapping[str, object],
    callback_assertions: Mapping[str, object],
    projection_assertions: Mapping[str, object],
    local_role_assertions: Mapping[str, object],
    csrf_write_assertions: Mapping[str, object],
    logout_assertions: Mapping[str, object],
    lane_assertions: Mapping[str, object],
    artifacts: Sequence[str],
    forbidden_values: Iterable[str],
) -> dict[str, object]:
    """Build and validate the final PR-0254 redacted manifest."""
    manifest: dict[str, object] = {
        "status": "ok",
        "command": command,
        "environment": environment,
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "app": DEFAULT_APP,
        "product_identity_realm": DEFAULT_REALM,
        "validated_prerequisite_artifacts": dict(validated_prerequisite_artifacts),
        "public_route_assertions": dict(public_route_assertions),
        "auth_entry_assertions": dict(auth_entry_assertions),
        "gateway_proxy_assertions": dict(gateway_proxy_assertions),
        "callback_assertions": dict(callback_assertions),
        "projection_assertions": dict(projection_assertions),
        "local_role_assertions": dict(local_role_assertions),
        "csrf_write_assertions": dict(csrf_write_assertions),
        "logout_assertions": dict(logout_assertions),
        "loopback_lane_assertions": dict(lane_assertions),
        "artifacts": list(artifacts),
        "redaction_checks": {
            "forbidden_exact_keys_absent": True,
            "forbidden_raw_marker_values_absent": True,
            "raw_urls_retained": False,
            "body_prefix_retained": False,
            "raw_email_retained": False,
            "raw_subject_retained": False,
            "cookies_or_csrf_retained": False,
            "signed_headers_retained": False,
            "jwt_or_signature_retained": False,
        },
    }
    assert_final_manifest_redacted(manifest, forbidden_values=forbidden_values)
    return manifest
