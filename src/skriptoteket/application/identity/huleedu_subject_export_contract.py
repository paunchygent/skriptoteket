"""Validate HuleEdu subject exports for local identity projection imports.

Purpose:
    Keep strict parsing and local role-matrix validation for sanitized HuleEdu
    subject export payloads separate from persistence.

Relationships:
    - Used by `huleedu_subject_export_consumer` before repository writes.
    - Validates the provider payload without trusting provider role claims for
      Skriptoteket authorization.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from skriptoteket.application.identity.email_validation import validate_email
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.identity.projections import ProductIdentityRealm

SUBJECT_EXPORT_SCHEMA_VERSION = "skriptoteket-proof-subject-export-v1"

DEFAULT_SUBJECT_ROLE_MATRIX: Mapping[str, Role] = {
    "skriptoteket-proof-user": Role.USER,
    "skriptoteket-proof-contributor": Role.CONTRIBUTOR,
    "skriptoteket-proof-admin": Role.ADMIN,
    "skriptoteket-proof-superuser": Role.SUPERUSER,
}


class HuleEduSubjectExportRecord(BaseModel):
    """One strict HuleEdu subject export row accepted by Skriptoteket."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, str_strip_whitespace=True)

    stable_account_key: str
    active_app: Literal["skriptoteket"]
    active_product_identity_realm: Literal["skriptoteket_standalone"]
    realm_subject_id: str
    email: str
    email_verified: bool = Field(strict=True)
    skriptoteket_role_hint: str
    huleedu_subject_id: str | None = None

    @field_validator("stable_account_key", "realm_subject_id")
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value:
            raise ValueError("value must be nonblank")
        return value

    @field_validator("stable_account_key")
    @classmethod
    def _stable_account_key_is_not_email(cls, value: str) -> str:
        if "@" in value:
            raise ValueError("stable_account_key must not be an email address")
        return value

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        try:
            return validate_email(email=value)
        except DomainError as exc:
            raise ValueError("email must be valid") from exc

    @field_validator("email_verified")
    @classmethod
    def _require_verified_email(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("email_verified must be true")
        return value

    @property
    def projection_realm(self) -> ProductIdentityRealm:
        """Return the enum realm after literal validation has fixed the value."""
        return ProductIdentityRealm(self.active_product_identity_realm)


class HuleEduSubjectExport(BaseModel):
    """Validated HuleEdu subject export payload."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["skriptoteket-proof-subject-export-v1"]
    active_app: Literal["skriptoteket"]
    active_product_identity_realm: Literal["skriptoteket_standalone"]
    generated_at: str | None = None
    accounts: list[HuleEduSubjectExportRecord]


def parse_huleedu_subject_export(
    payload: object,
    *,
    role_matrix: Mapping[str, Role] | None = None,
) -> HuleEduSubjectExport:
    """Parse and validate a HuleEdu export payload before any repository writes."""
    export_payload = _extract_export_payload(payload)
    try:
        export = HuleEduSubjectExport.model_validate(export_payload)
    except ValidationError as exc:
        raise build_subject_export_validation_error(
            "invalid_export_schema",
            field=_first_validation_field(exc),
        ) from exc

    _validate_record_uniqueness(export=export)
    _validate_role_matrix(export=export, role_matrix=role_matrix or DEFAULT_SUBJECT_ROLE_MATRIX)
    return export


def build_subject_export_validation_error(
    reason: str,
    *,
    field: str | None = None,
    stable_account_key: str | None = None,
) -> DomainError:
    """Build a sanitized validation error for export contract violations."""
    details: dict[str, object] = {"reason": reason}
    if field is not None:
        details["field"] = field
    if stable_account_key is not None:
        details["stable_account_key"] = stable_account_key
    return DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message="Invalid HuleEdu subject export",
        details=details,
    )


def _extract_export_payload(payload: object) -> Mapping[str, object]:
    if not isinstance(payload, dict):
        raise build_subject_export_validation_error("invalid_export_payload")

    if "export" in payload:
        if payload.get("status") != "ok":
            raise build_subject_export_validation_error("provider_export_not_ok", field="status")
        if payload.get("errors"):
            raise build_subject_export_validation_error(
                "provider_export_contains_errors", field="errors"
            )
        export = payload["export"]
        if not isinstance(export, dict):
            raise build_subject_export_validation_error("invalid_export_payload", field="export")
        return export

    return payload


def _validate_record_uniqueness(*, export: HuleEduSubjectExport) -> None:
    subject_keys: dict[tuple[str, str], str] = {}
    emails: dict[str, str] = {}
    stable_keys: set[str] = set()
    for record in export.accounts:
        if record.stable_account_key in stable_keys:
            raise build_subject_export_validation_error(
                "duplicate_stable_account_key",
                field="stable_account_key",
                stable_account_key=record.stable_account_key,
            )
        stable_keys.add(record.stable_account_key)

        subject_key = (record.projection_realm.value, record.realm_subject_id)
        if subject_key in subject_keys:
            raise build_subject_export_validation_error(
                "duplicate_subject_record",
                field="realm_subject_id",
                stable_account_key=record.stable_account_key,
            )
        subject_keys[subject_key] = record.stable_account_key

        if record.email in emails:
            raise build_subject_export_validation_error(
                "duplicate_email_record",
                field="email",
                stable_account_key=record.stable_account_key,
            )
        emails[record.email] = record.stable_account_key


def _validate_role_matrix(
    *,
    export: HuleEduSubjectExport,
    role_matrix: Mapping[str, Role],
) -> None:
    for record in export.accounts:
        target_role = role_matrix.get(record.stable_account_key)
        if target_role is None:
            raise build_subject_export_validation_error(
                "unsupported_stable_account_key",
                field="stable_account_key",
                stable_account_key=record.stable_account_key,
            )
        if record.skriptoteket_role_hint != target_role.value:
            raise build_subject_export_validation_error(
                "role_hint_matrix_mismatch",
                field="skriptoteket_role_hint",
                stable_account_key=record.stable_account_key,
            )


def _first_validation_field(exc: ValidationError) -> str | None:
    first_error = next(iter(exc.errors()), None)
    if first_error is None:
        return None
    location = first_error.get("loc", ())
    if not location:
        return None
    return ".".join(str(part) for part in location)
