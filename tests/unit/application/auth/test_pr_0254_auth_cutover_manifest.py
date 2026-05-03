"""Unit tests for PR-0254 auth-cutover manifest validation.

Purpose:
    Prove PR-0254 consumes retained upstream proof artifacts as sanitized
    prerequisites and emits only redacted final cutover evidence.

Relationships:
    - Exercises `scripts._pr_0254_auth_cutover_manifest` before the live
      Playwright cross-process smoke runs.
    - Reuses the same HuleEdu TASK-0327 contract consumed by PR-0262 while
      adding PR-0254-specific preflight and final-manifest assertions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._pr_0254_auth_cutover_manifest import (
    AuthCutoverManifestError,
    build_manifest,
    validate_huleedu_task_0326_artifact,
    validate_prerequisite_artifacts,
)

RAW_EMAIL = "proof-user@example.test"
RAW_SUBJECT = "raw-provider-subject-123"


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _provider_action(
    name: str,
    *,
    gateway_path: str,
    frontend_path: str | None = None,
    method: str = "GET",
    status_code: int = 303,
    token_present: bool = False,
) -> dict[str, object]:
    return {
        "frontend_path": frontend_path,
        "gateway_path": gateway_path,
        "method": method,
        "name": name,
        "status_code": status_code,
        "token_present": token_present,
    }


def _huleedu_task_0326_artifact() -> dict[str, object]:
    return {
        "status": "ok",
        "mode": "apply",
        "export": {
            "schema_version": "huleedu.skriptoteket.subject_export.v1",
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "accounts": [
                {
                    "active_app": "skriptoteket",
                    "active_product_identity_realm": "skriptoteket_standalone",
                    "email": RAW_EMAIL,
                    "email_verified": True,
                    "huleedu_subject_id": "huleedu-subject-123",
                    "realm_subject_id": RAW_SUBJECT,
                    "skriptoteket_role_hint": "contributor",
                    "stable_account_key": "skriptoteket-proof-contributor",
                }
            ],
        },
    }


def _huleedu_task_0327_artifact() -> dict[str, object]:
    return {
        "command": {
            "app": "skriptoteket",
            "artifact_dir": ".artifacts/skriptoteket-lifecycle-proof/dev",
            "base_url": "http://localhost:8080",
            "confirm_side_effects": True,
            "mode": "apply",
            "next_path": "/editor",
            "product_identity_realm": "skriptoteket_standalone",
            "return_to": "http://localhost:5173/auth/callback",
            "signed_context_probe_path": "/api/v1/diagnostics/huleedu-internal-identity",
        },
        "proof": {
            "account_action": "account_exists_safe_rerun",
            "actions": [
                _provider_action(
                    "login_direct_landing",
                    gateway_path="/auth/login",
                    frontend_path="/login",
                ),
                _provider_action(
                    "registration_direct_landing",
                    gateway_path="/auth/register",
                    frontend_path="/register",
                ),
                _provider_action(
                    "forgot_password_direct_landing",
                    gateway_path="/auth/password-reset",
                    frontend_path="/password-reset",
                ),
                _provider_action(
                    "reset_completion_direct_landing",
                    gateway_path="/auth/password-reset",
                    frontend_path="/password-reset",
                    token_present=True,
                ),
                _provider_action(
                    "email_verification_direct_landing",
                    gateway_path="/auth/email-verification",
                    frontend_path="/email-verification",
                    token_present=True,
                ),
                _provider_action(
                    "registration_submit",
                    gateway_path="/v1/auth/register",
                    method="POST",
                    status_code=400,
                ),
                _provider_action(
                    "email_verification_request",
                    gateway_path="/v1/auth/request-email-verification",
                    method="POST",
                    status_code=200,
                ),
                _provider_action(
                    "forgot_password_request",
                    gateway_path="/v1/auth/request-password-reset",
                    method="POST",
                    status_code=200,
                ),
                _provider_action(
                    "reset_password_link_landing",
                    gateway_path="/auth/password-reset",
                    status_code=303,
                    token_present=True,
                ),
                _provider_action(
                    "reset_password_complete",
                    gateway_path="/v1/auth/reset-password",
                    method="POST",
                    status_code=200,
                ),
                _provider_action(
                    "login_submit",
                    gateway_path="/v1/auth/login",
                    method="POST",
                    status_code=200,
                ),
                _provider_action(
                    "session_claims",
                    gateway_path="/v1/auth/session",
                    status_code=200,
                ),
                _provider_action(
                    "signed_context_probe",
                    gateway_path="/api/v1/diagnostics/huleedu-internal-identity",
                    status_code=200,
                ),
            ],
            "mode": "apply",
            "reset_delivery": "fresh_link_consumed",
            "session_claims": {
                "active_app": "skriptoteket",
                "active_product_identity_realm": "skriptoteket_standalone",
                "email": RAW_EMAIL,
                "email_verified": True,
                "realm_subject_id": RAW_SUBJECT,
            },
            "signed_context_claims": {
                "active_app": "skriptoteket",
                "active_product_identity_realm": "skriptoteket_standalone",
                "email_present": True,
                "email_verified": True,
                "linked_identity_matches_realm_subject": True,
                "linked_identity_realm_present": True,
                "realm_subject_id_present": True,
                "subject_claim_present": True,
                "subject_matches_realm_subject": True,
            },
            "status": "ok",
            "verification_delivery": "already_verified_or_no_new_verification_message",
        },
    }


def _pr_0261_manifest() -> dict[str, object]:
    action_names = [
        "login",
        "register",
        "password-reset-request",
        "password-reset-completion",
        "email-verification",
    ]
    return {
        "actions": [
            {
                "name": name,
                "provider": {
                    "app": "skriptoteket",
                    "path": "/auth/login",
                    "product_identity_realm": "skriptoteket_standalone",
                },
            }
            for name in action_names
        ],
        "app": "skriptoteket",
        "consumer_probe": {
            "claims": {
                "active_app": "skriptoteket",
                "active_product_identity_realm": "skriptoteket_standalone",
            },
            "status": "ok",
        },
        "product_identity_realm": "skriptoteket_standalone",
        "redaction_checks": {
            "raw_session_material_retained": False,
            "raw_signed_context_retained": False,
            "raw_tokens_retained": False,
        },
        "status": "ok",
    }


def _pr_0262_manifest() -> dict[str, object]:
    return {
        "app": "skriptoteket",
        "environment": "local-nonprod",
        "local_role_assertions": {
            "expected_local_role": "contributor",
            "observed_local_role": "contributor",
            "role_matches_expected": True,
        },
        "product_identity_realm": "skriptoteket_standalone",
        "redaction_checks": {
            "cookies_or_csrf_retained": False,
            "forbidden_exact_keys_absent": True,
            "forbidden_raw_marker_values_absent": True,
            "raw_email_retained": False,
            "raw_jwt_or_signature_retained": False,
            "raw_magic_link_retained": False,
            "raw_realm_subject_id_retained": False,
            "raw_reset_or_verification_token_retained": False,
            "raw_signed_headers_retained": False,
        },
        "status": "ok",
        "upstream_huleedu_task_0327": {"status": "ok", "validated": True},
    }


def _prerequisite_files(tmp_path: Path) -> dict[str, Path]:
    return {
        "huleedu_task_0326": _write_json(
            tmp_path / "huleedu-task-0326.json",
            _huleedu_task_0326_artifact(),
        ),
        "huleedu_task_0327": _write_json(
            tmp_path / "huleedu-task-0327.json",
            _huleedu_task_0327_artifact(),
        ),
        "pr_0261": _write_json(tmp_path / "pr-0261.json", _pr_0261_manifest()),
        "pr_0262": _write_json(tmp_path / "pr-0262.json", _pr_0262_manifest()),
    }


def test_validates_prerequisite_artifacts_without_retaining_raw_identity(
    tmp_path: Path,
) -> None:
    files = _prerequisite_files(tmp_path)

    validations = validate_prerequisite_artifacts(
        huleedu_task_0326_path=files["huleedu_task_0326"],
        huleedu_task_0327_path=files["huleedu_task_0327"],
        pr_0261_path=files["pr_0261"],
        pr_0262_path=files["pr_0262"],
    )

    assert set(validations) == {"huleedu_task_0326", "huleedu_task_0327", "pr_0261", "pr_0262"}
    assert all(summary["status"] == "ok" for summary in validations.values())
    assert all(summary["validated"] is True for summary in validations.values())
    retained = json.dumps(validations, sort_keys=True)
    assert RAW_EMAIL not in retained
    assert RAW_SUBJECT not in retained


def test_rejects_task_0326_export_for_wrong_realm() -> None:
    payload = _huleedu_task_0326_artifact()
    export = payload["export"]
    assert isinstance(export, dict)
    export["active_product_identity_realm"] = "other"

    with pytest.raises(AuthCutoverManifestError, match="active_product_identity_realm"):
        validate_huleedu_task_0326_artifact(payload, artifact_path=Path("/tmp/task-0326.json"))


def test_build_manifest_rejects_raw_url_keys() -> None:
    with pytest.raises(AuthCutoverManifestError, match="forbidden retained keys"):
        build_manifest(
            environment="local-nonprod",
            run_id="20260413T140000Z",
            command="pdm run auth-cutover-proof",
            validated_prerequisite_artifacts={},
            public_route_assertions={"raw_url": "http://localhost:5173/editor"},
            auth_entry_assertions={},
            gateway_proxy_assertions={},
            callback_assertions={},
            projection_assertions={},
            local_role_assertions={},
            csrf_write_assertions={},
            logout_assertions={},
            lane_assertions={},
            artifacts=[],
            forbidden_values=[],
        )


def test_build_manifest_rejects_forbidden_marker_values() -> None:
    with pytest.raises(AuthCutoverManifestError, match="forbidden raw marker"):
        build_manifest(
            environment="local-nonprod",
            run_id="20260413T140000Z",
            command="pdm run auth-cutover-proof",
            validated_prerequisite_artifacts={},
            public_route_assertions={"status": "ok"},
            auth_entry_assertions={},
            gateway_proxy_assertions={},
            callback_assertions={"final_path": RAW_SUBJECT},
            projection_assertions={},
            local_role_assertions={},
            csrf_write_assertions={},
            logout_assertions={},
            lane_assertions={},
            artifacts=[],
            forbidden_values=[RAW_SUBJECT],
        )


def test_build_manifest_accepts_sanitized_final_contract() -> None:
    manifest = build_manifest(
        environment="local-nonprod",
        run_id="20260413T140000Z",
        command="pdm run auth-cutover-proof",
        validated_prerequisite_artifacts={
            "pr_0262": {"status": "ok", "validated": True, "redacted": True}
        },
        public_route_assertions={"bootstrap_status": 200},
        auth_entry_assertions={"gateway_path": "/auth/login"},
        gateway_proxy_assertions={"direct_backend_shortcut_observed": False},
        callback_assertions={"final_path": "/editor"},
        projection_assertions={"local_projection_resolved": True},
        local_role_assertions={"role_matches_expected": True},
        csrf_write_assertions={"csrf_protected_write_succeeded": True},
        logout_assertions={"shared_session_invalidated": True},
        lane_assertions={"localhost": {"status": "ok"}},
        artifacts=[".artifacts/pr-0254/editor-after-callback.png"],
        forbidden_values=[RAW_EMAIL, RAW_SUBJECT],
    )

    assert manifest["status"] == "ok"
    assert manifest["app"] == "skriptoteket"
    assert manifest["product_identity_realm"] == "skriptoteket_standalone"
    redaction_checks = manifest["redaction_checks"]
    assert isinstance(redaction_checks, dict)
    assert redaction_checks["raw_urls_retained"] is False
