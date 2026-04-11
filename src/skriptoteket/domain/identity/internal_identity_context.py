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
    org_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    roles: list[str]
    grants: list[str]
    policy_version: str = Field(min_length=1)
    iat: int
    exp: int
    jti: str = Field(min_length=1)
    active_context: dict[str, Any] | None = None
    feature_flags: list[str] = Field(default_factory=list)
    source_app: str | None = None

    @field_validator(
        "iss", "aud", "sub", "session_id", "org_id", "tenant_id", "policy_version", "jti"
    )
    @classmethod
    def validate_non_blank_required_strings(cls, value: str) -> str:
        """Reject blank required contract fields after trimming whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("roles", "grants")
    @classmethod
    def validate_non_blank_string_lists(cls, values: list[str]) -> list[str]:
        """Reject blank role/grant entries while preserving explicit empty lists."""
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("list entries must be non-blank strings")
        return values
