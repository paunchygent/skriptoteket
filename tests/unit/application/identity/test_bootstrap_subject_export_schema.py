"""Unit tests for HuleEdu subject export validation.

Purpose:
    Prove the Skriptoteket consumer accepts only the frozen provider schema
    before any local user or projection writes can occur.

Relationships:
    - Exercises `huleedu_subject_export_contract`.
    - Complements role-matrix application tests in the neighboring module.
"""

from __future__ import annotations

import pytest

from skriptoteket.application.identity.huleedu_subject_export_contract import (
    SUBJECT_EXPORT_SCHEMA_VERSION,
    parse_huleedu_subject_export,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "stable_account_key": "skriptoteket-proof-user",
        "active_app": "skriptoteket",
        "active_product_identity_realm": "skriptoteket_standalone",
        "realm_subject_id": "realm-user-1",
        "email": "skriptoteket-proof-user@hule.education",
        "email_verified": True,
        "skriptoteket_role_hint": "user",
        "huleedu_subject_id": "diagnostic-huleedu-subject",
    }
    record.update(overrides)
    return record


def _provider_envelope(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "status": "ok",
        "errors": [],
        "mode": "verify",
        "export": {
            "schema_version": SUBJECT_EXPORT_SCHEMA_VERSION,
            "active_app": "skriptoteket",
            "active_product_identity_realm": "skriptoteket_standalone",
            "generated_at": "2026-04-13T05:06:54+00:00",
            "accounts": records,
        },
    }


def _assert_export_error(payload: object, *, reason: str, field: str | None = None) -> None:
    with pytest.raises(DomainError) as exc_info:
        parse_huleedu_subject_export(payload)

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details["reason"] == reason
    if field is not None:
        assert field in str(exc_info.value.details.get("field"))


def test_provider_envelope_validates_to_account_records() -> None:
    export = parse_huleedu_subject_export(
        _provider_envelope(
            [
                _record(),
                _record(
                    stable_account_key="skriptoteket-proof-admin",
                    realm_subject_id="realm-admin-1",
                    email="skriptoteket-proof-admin@hule.education",
                    skriptoteket_role_hint="admin",
                ),
            ]
        )
    )

    assert export.schema_version == SUBJECT_EXPORT_SCHEMA_VERSION
    assert [record.stable_account_key for record in export.accounts] == [
        "skriptoteket-proof-user",
        "skriptoteket-proof-admin",
    ]


def test_fully_versioned_export_object_is_accepted_without_provider_envelope() -> None:
    export = parse_huleedu_subject_export(_provider_envelope([_record()])["export"])

    assert export.active_app == "skriptoteket"
    assert export.accounts[0].realm_subject_id == "realm-user-1"


def test_bare_array_is_rejected_instead_of_synthesizing_export_contract() -> None:
    _assert_export_error([_record()], reason="invalid_export_payload")


def test_unversioned_accounts_object_is_rejected() -> None:
    _assert_export_error(
        {"accounts": [_record()]},
        reason="invalid_export_schema",
        field="schema_version",
    )


@pytest.mark.parametrize(
    "missing_field",
    ["schema_version", "active_app", "active_product_identity_realm"],
)
def test_top_level_contract_fields_are_required(missing_field: str) -> None:
    payload = _provider_envelope([_record()])
    export = payload["export"]
    assert isinstance(export, dict)
    export.pop(missing_field)

    _assert_export_error(payload, reason="invalid_export_schema", field=missing_field)


@pytest.mark.parametrize(
    ("provider_fields", "reason", "field"),
    [
        ({"status": "failed"}, "provider_export_not_ok", "status"),
        ({"errors": ["account drift"]}, "provider_export_contains_errors", "errors"),
    ],
)
def test_provider_envelope_must_be_successful(
    provider_fields: dict[str, object],
    reason: str,
    field: str,
) -> None:
    payload = _provider_envelope([_record()])
    payload.update(provider_fields)

    _assert_export_error(payload, reason=reason, field=field)


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"active_app": "huleedu"}, "active_app"),
        ({"active_product_identity_realm": "huleedu_school"}, "active_product_identity_realm"),
        ({"email_verified": False}, "email_verified"),
        ({"email_verified": "true"}, "email_verified"),
        ({"extra_provider_role": "admin"}, "extra_provider_role"),
    ],
)
def test_record_schema_fails_closed_for_wrong_scope_or_loose_fields(
    overrides: dict[str, object],
    field: str,
) -> None:
    _assert_export_error(
        _provider_envelope([_record(**overrides)]),
        reason="invalid_export_schema",
        field=field,
    )


def test_huleedu_subject_id_cannot_repair_missing_realm_subject() -> None:
    record = _record(realm_subject_id=None, huleedu_subject_id="umbrella-subject")

    _assert_export_error(
        _provider_envelope([record]),
        reason="invalid_export_schema",
        field="realm_subject_id",
    )


def test_duplicate_subject_and_email_records_fail_before_writes() -> None:
    duplicate_subject = [
        _record(),
        _record(
            stable_account_key="skriptoteket-proof-admin",
            email="skriptoteket-proof-admin@hule.education",
            skriptoteket_role_hint="admin",
        ),
    ]
    _assert_export_error(
        _provider_envelope(duplicate_subject),
        reason="duplicate_subject_record",
        field="realm_subject_id",
    )

    duplicate_email = [
        _record(),
        _record(
            stable_account_key="skriptoteket-proof-admin",
            realm_subject_id="realm-admin-1",
            skriptoteket_role_hint="admin",
        ),
    ]
    _assert_export_error(
        _provider_envelope(duplicate_email),
        reason="duplicate_email_record",
        field="email",
    )


def test_role_hint_must_match_skriptoteket_owned_matrix() -> None:
    _assert_export_error(
        _provider_envelope([_record(skriptoteket_role_hint="admin")]),
        reason="role_hint_matrix_mismatch",
        field="skriptoteket_role_hint",
    )

    _assert_export_error(
        _provider_envelope(
            [
                _record(
                    stable_account_key="provider-owned-surprise-key",
                    realm_subject_id="realm-surprise-1",
                    email="surprise@hule.education",
                )
            ]
        ),
        reason="unsupported_stable_account_key",
        field="stable_account_key",
    )
