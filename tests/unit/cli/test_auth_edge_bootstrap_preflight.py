"""Unit tests for the local auth-edge bootstrap preflight.

Purpose:
    Prove the PR-0283 preflight detects stale HuleEdu subject exports before
    browser proof reaches the activation-required screen.

Relationships:
    - Exercises the CLI preflight's provider-export validation.
    - Complements the subject export consumer tests that cover DB writes.
"""

from __future__ import annotations

from skriptoteket.application.identity.huleedu_subject_export_contract import (
    SUBJECT_EXPORT_SCHEMA_VERSION,
    parse_huleedu_subject_export,
)
from skriptoteket.cli.commands.auth_edge_bootstrap_preflight import _validate_export_matrix


def _record(
    *,
    stable_account_key: str,
    email: str,
    role: str,
    subject: str,
) -> dict[str, object]:
    return {
        "stable_account_key": stable_account_key,
        "active_app": "skriptoteket",
        "active_product_identity_realm": "skriptoteket_standalone",
        "realm_subject_id": subject,
        "email": email,
        "email_verified": True,
        "skriptoteket_role_hint": role,
        "huleedu_subject_id": subject,
    }


def _export(records: list[dict[str, object]]) -> object:
    return {
        "schema_version": SUBJECT_EXPORT_SCHEMA_VERSION,
        "active_app": "skriptoteket",
        "active_product_identity_realm": "skriptoteket_standalone",
        "accounts": records,
    }


def test_validate_export_matrix_accepts_local_dev_rbac_set() -> None:
    """The fresh HuleEdu local export should cover all Skriptoteket proof roles."""
    export = parse_huleedu_subject_export(
        _export(
            [
                _record(
                    stable_account_key="skriptoteket-proof-user",
                    email="skriptoteket-proof-user@local.dev",
                    role="user",
                    subject="subject-user",
                ),
                _record(
                    stable_account_key="skriptoteket-proof-contributor",
                    email="skriptoteket-proof-contributor@local.dev",
                    role="contributor",
                    subject="subject-contributor",
                ),
                _record(
                    stable_account_key="skriptoteket-proof-admin",
                    email="skriptoteket-proof-admin@local.dev",
                    role="admin",
                    subject="subject-admin",
                ),
                _record(
                    stable_account_key="skriptoteket-proof-superuser",
                    email="superuser@local.dev",
                    role="superuser",
                    subject="subject-superuser",
                ),
            ]
        )
    )

    assert _validate_export_matrix(export) == []


def test_validate_export_matrix_rejects_stale_hule_education_matrix() -> None:
    """The old three-account hule.education export is stale for PR-0283."""
    export = parse_huleedu_subject_export(
        _export(
            [
                _record(
                    stable_account_key="skriptoteket-proof-user",
                    email="skriptoteket-proof-user@hule.education",
                    role="user",
                    subject="subject-user",
                ),
                _record(
                    stable_account_key="skriptoteket-proof-admin",
                    email="skriptoteket-proof-admin@hule.education",
                    role="admin",
                    subject="subject-admin",
                ),
                _record(
                    stable_account_key="skriptoteket-proof-superuser",
                    email="skriptoteket-proof-superuser@hule.education",
                    role="superuser",
                    subject="subject-superuser",
                ),
            ]
        )
    )

    issues = _validate_export_matrix(export)

    assert {issue.code for issue in issues} == {"provider_export_stale"}
    assert any(issue.stable_account_key == "skriptoteket-proof-contributor" for issue in issues)
    assert any(issue.email == "skriptoteket-proof-superuser@hule.education" for issue in issues)
