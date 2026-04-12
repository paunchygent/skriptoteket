"""HuleEdu gateway internal identity context contract.

Purpose:
    Define the signed `InternalIdentityContextV1` payload and transport header
    names consumed by Skriptoteket when HuleEdu Gateway proves browser identity.

Relationships:
    - Mirrors the HuleEdu provider contract accepted for PR-0255.
    - Verified by `skriptoteket.infrastructure.security.huleedu_internal_identity`.
    - Consumed by the app-local projection resolver for continuation bootstrap.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

INTERNAL_IDENTITY_CONTEXT_VERSION = 1
INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER = "X-Huledu-Identity-Context-Version"
INTERNAL_IDENTITY_CONTEXT_HEADER = "X-Huledu-Identity-Context"
INTERNAL_IDENTITY_KEY_ID_HEADER = "X-Huledu-Identity-Key-Id"
INTERNAL_IDENTITY_SIGNATURE_HEADER = "X-Huledu-Identity-Signature"
INTERNAL_IDENTITY_SIGNATURE_PREFIX = "rs256="


class InternalIdentityContextV1(BaseModel):
    """Canonical HuleEdu Gateway-to-service identity propagation payload."""

    model_config = ConfigDict(extra="forbid")

    context_version: Literal[1] = 1
    iss: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    sub: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    org_id: str | None = None
    tenant_id: str | None = None
    roles: list[str]
    grants: list[str]
    policy_version: str = Field(min_length=1)
    iat: int
    exp: int
    jti: str = Field(min_length=1)
    active_context: dict[str, Any] | None = None
    feature_flags: list[str] = Field(default_factory=list)
    source_app: str | None = None
    active_app: str | None = None
    active_product_identity_realm: str | None = None
    realm_subject_id: str | None = None
    linked_identity_ids: dict[str, str] | None = None

    @field_validator("iss", "aud", "sub", "session_id", "policy_version", "jti")
    @classmethod
    def validate_non_blank_required_strings(cls, value: str) -> str:
        """Reject blank required contract fields after trimming whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator(
        "org_id",
        "tenant_id",
        "source_app",
        "active_app",
        "active_product_identity_realm",
        "realm_subject_id",
    )
    @classmethod
    def validate_optional_non_blank_strings(cls, value: str | None) -> str | None:
        """Reject blank optional string fields while allowing omitted context."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank when provided")
        return normalized

    @field_validator("roles", "grants")
    @classmethod
    def validate_non_blank_string_lists(cls, values: list[str]) -> list[str]:
        """Reject blank role/grant entries while preserving explicit empty lists."""
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("list entries must be non-blank strings")
        return values

    @field_validator("linked_identity_ids")
    @classmethod
    def validate_linked_identity_ids(
        cls,
        values: dict[str, str] | None,
    ) -> dict[str, str] | None:
        """Reject blank linked realm ids while preserving optional linking."""
        if values is None:
            return None
        normalized: dict[str, str] = {}
        for realm, subject_id in values.items():
            normalized_realm = realm.strip()
            normalized_subject_id = subject_id.strip()
            if not normalized_realm or not normalized_subject_id:
                raise ValueError("linked identity entries must be non-blank strings")
            normalized[normalized_realm] = normalized_subject_id
        return normalized
