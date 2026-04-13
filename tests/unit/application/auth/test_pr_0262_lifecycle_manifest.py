"""Unit tests for PR-0262 lifecycle proof manifest validation.

Purpose:
    Prove the PR-0262 retained artifact contract accepts the approved HuleEdu
    sanitized diagnostics shape while rejecting missing claims or raw identity
    retention.

Relationships:
    - Exercises `scripts._pr_0262_lifecycle_manifest` before Playwright live
      proof runs.
    - Complements app-continuation route tests that prove local projection
      resolution behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._pr_0262_lifecycle_manifest import (
    HuleEduTask0327Validation,
    LifecycleProofValidationError,
    assert_manifest_redacted,
    build_manifest,
    validate_huleedu_task_0327_artifact,
)

RAW_EMAIL = "proof-user@example.test"
RAW_SUBJECT = "raw-provider-subject-123"


def _action(
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


def _huleedu_artifact() -> dict[str, object]:
    return {
        "command": {
            "app": "skriptoteket",
            "artifact_dir": ".artifacts/skriptoteket-lifecycle-proof/dev",
            "base_url": "http://localhost:8080",
            "confirm_side_effects": True,
            "mode": "apply",
            "next_path": "/tools",
            "product_identity_realm": "skriptoteket_standalone",
            "return_to": "http://localhost:5173/auth/callback",
            "signed_context_probe_path": "/api/v1/diagnostics/huleedu-internal-identity",
        },
        "proof": {
            "account_action": "account_exists_safe_rerun",
            "actions": [
                _action(
                    "login_direct_landing",
                    gateway_path="/auth/login",
                    frontend_path="/login",
                ),
                _action(
                    "registration_direct_landing",
                    gateway_path="/auth/register",
                    frontend_path="/register",
                ),
                _action(
                    "forgot_password_direct_landing",
                    gateway_path="/auth/password-reset",
                    frontend_path="/password-reset",
                ),
                _action(
                    "reset_completion_direct_landing",
                    gateway_path="/auth/password-reset",
                    frontend_path="/password-reset",
                    token_present=True,
                ),
                _action(
                    "email_verification_direct_landing",
                    gateway_path="/auth/email-verification",
                    frontend_path="/email-verification",
                    token_present=True,
                ),
                _action(
                    "registration_submit",
                    gateway_path="/v1/auth/register",
                    frontend_path=None,
                    method="POST",
                    status_code=400,
                ),
                _action(
                    "email_verification_request",
                    gateway_path="/v1/auth/request-email-verification",
                    frontend_path=None,
                    method="POST",
                    status_code=200,
                ),
                _action(
                    "forgot_password_request",
                    gateway_path="/v1/auth/request-password-reset",
                    frontend_path=None,
                    method="POST",
                    status_code=200,
                ),
                _action(
                    "reset_password_link_landing",
                    gateway_path="/auth/password-reset",
                    frontend_path="/password-reset",
                    status_code=303,
                    token_present=True,
                ),
                _action(
                    "reset_password_complete",
                    gateway_path="/v1/auth/reset-password",
                    frontend_path=None,
                    method="POST",
                    status_code=200,
                ),
                _action(
                    "login_submit",
                    gateway_path="/v1/auth/login",
                    frontend_path=None,
                    method="POST",
                    status_code=200,
                ),
                _action(
                    "session_claims",
                    gateway_path="/v1/auth/session",
                    frontend_path=None,
                    status_code=200,
                ),
                _action(
                    "signed_context_probe",
                    gateway_path="/api/v1/diagnostics/huleedu-internal-identity",
                    frontend_path=None,
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


def _validated() -> HuleEduTask0327Validation:
    return validate_huleedu_task_0327_artifact(
        _huleedu_artifact(),
        artifact_path=Path("/tmp/huleedu-task-0327.json"),
    )


def test_accepts_huleedu_status_ok_artifact_without_retaining_raw_identity() -> None:
    validation = _validated()

    assert validation.provider_subject == RAW_SUBJECT
    assert validation.provider_email == RAW_EMAIL
    retained_summary = json.dumps(validation.summary, sort_keys=True)
    assert RAW_SUBJECT not in retained_summary
    assert RAW_EMAIL not in retained_summary
    assert validation.summary["status"] == "ok"
    assert validation.summary["signed_context_probe_path"] == (
        "/api/v1/diagnostics/huleedu-internal-identity"
    )
    assert validation.summary["direct_action_count"] == 5


def test_rejects_missing_sanitized_signed_context_claim() -> None:
    payload = _huleedu_artifact()
    signed_claims = payload["proof"]["signed_context_claims"]  # type: ignore[index]
    signed_claims["subject_matches_realm_subject"] = False  # type: ignore[index]

    with pytest.raises(LifecycleProofValidationError, match="subject_matches_realm_subject"):
        validate_huleedu_task_0327_artifact(payload, artifact_path=Path("/tmp/artifact.json"))


def test_rejects_missing_direct_action_landing() -> None:
    payload = _huleedu_artifact()
    proof = payload["proof"]  # type: ignore[index]
    proof["actions"] = [  # type: ignore[index]
        action
        for action in proof["actions"]  # type: ignore[index]
        if action["name"] != "email_verification_direct_landing"
    ]

    with pytest.raises(LifecycleProofValidationError, match="email_verification_direct_landing"):
        validate_huleedu_task_0327_artifact(payload, artifact_path=Path("/tmp/artifact.json"))


def test_build_manifest_rejects_raw_subject_or_email_markers() -> None:
    validation = _validated()

    with pytest.raises(LifecycleProofValidationError, match="forbidden raw marker"):
        build_manifest(
            environment="local-nonprod",
            run_id="20260413T130000Z",
            huleedu_validation=validation,
            controlled_account_key="skriptoteket-proof-contributor",
            callback_assertions={"browser_callback": {"final_path": RAW_SUBJECT}},
            projection_assertions={"projection_resolved": True},
            local_role_assertions={"role_matches_expected": True},
            screenshot_paths=[],
            log_paths=[],
            forbidden_values=[RAW_SUBJECT, RAW_EMAIL],
        )


def test_build_manifest_retains_only_sanitized_decision_evidence() -> None:
    validation = _validated()

    manifest = build_manifest(
        environment="local-nonprod",
        run_id="20260413T130000Z",
        huleedu_validation=validation,
        controlled_account_key="skriptoteket-proof-contributor",
        callback_assertions={"browser_callback": {"final_path": "/editor"}},
        projection_assertions={"projection_resolved": True},
        local_role_assertions={
            "expected_local_role": "contributor",
            "observed_local_role": "contributor",
            "role_matches_expected": True,
        },
        screenshot_paths=[".artifacts/proof.png"],
        log_paths=[],
        forbidden_values=[RAW_SUBJECT, RAW_EMAIL],
    )

    serialized = json.dumps(manifest, sort_keys=True)
    assert RAW_SUBJECT not in serialized
    assert RAW_EMAIL not in serialized
    assert manifest["status"] == "ok"
    assert manifest["upstream_huleedu_task_0327"]["validated"] is True  # type: ignore[index]
    assert manifest["redaction_checks"]["raw_realm_subject_id_retained"] is False  # type: ignore[index]
    assert_manifest_redacted(manifest, forbidden_values=[RAW_SUBJECT, RAW_EMAIL])
