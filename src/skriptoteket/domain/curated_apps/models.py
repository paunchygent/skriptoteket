"""Curated-app metadata models and deterministic identities.

Purpose:
  Define the immutable registry metadata used to discover, authorize, and
  launch first-class curated apps inside Skriptoteket.

Relationships:
  - Shared by the in-memory curated app registry and catalog/discovery flows.
  - Provides deterministic `tool_id` generation from stable `app_id` values.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from skriptoteket.domain.identity.models import Role

_CURATED_APPS_NAMESPACE = uuid5(NAMESPACE_URL, "skriptoteket.curated_apps")


def curated_app_tool_id(*, app_id: str) -> UUID:
    normalized = app_id.strip()
    if not normalized:
        raise ValueError("app_id is required")
    return uuid5(_CURATED_APPS_NAMESPACE, normalized)


class CuratedAppUiMode(StrEnum):
    GENERIC_OK = "generic_ok"
    BESPOKE_REQUIRED = "bespoke_required"


class CuratedAppPublicAccessProfile(StrEnum):
    AUTHENTICATED_ONLY = "authenticated_only"
    PUBLIC_STATELESS = "public_stateless"
    PUBLIC_BROWSER_RUNTIME = "public_browser_runtime"
    PUBLIC_BROWSER_WORKSPACE_WITH_UPGRADE = "public_browser_workspace_with_upgrade"


class CuratedAppPublicRuntimeStatus(StrEnum):
    CONTRACT_ONLY = "contract_only"
    ACTIVE = "active"


class CuratedAppPlacement(BaseModel):
    """Where an app appears in Katalog (profession/category browse tree)."""

    model_config = ConfigDict(frozen=True)

    profession_slug: str
    category_slug: str

    @field_validator("profession_slug", "category_slug")
    @classmethod
    def _validate_slug(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("slug is required")
        if len(normalized) > 64:
            raise ValueError("slug must be 64 characters or less")
        return normalized


class CuratedAppPublicCapability(BaseModel):
    """Scoped public capability exposed by an otherwise authenticated app."""

    model_config = ConfigDict(frozen=True)

    scope: str
    profile: CuratedAppPublicAccessProfile
    runtime_status: CuratedAppPublicRuntimeStatus = CuratedAppPublicRuntimeStatus.CONTRACT_ONLY

    @field_validator("scope")
    @classmethod
    def _validate_scope(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("public capability scope is required")
        if len(normalized) > 64:
            raise ValueError("public capability scope must be 64 characters or less")
        if normalized != normalized.lower():
            raise ValueError("public capability scope must be lowercase")
        if not all(
            (character.isascii() and character.isalnum()) or character == "_"
            for character in normalized
        ):
            raise ValueError(
                "public capability scope may only contain lowercase letters, digits, and _"
            )
        return normalized

    @field_validator("profile")
    @classmethod
    def _validate_public_profile(
        cls, value: CuratedAppPublicAccessProfile
    ) -> CuratedAppPublicAccessProfile:
        if value is CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY:
            raise ValueError("public capability profile must be a public access profile")
        return value


class CuratedAppDefinition(BaseModel):
    """Curated app metadata discovered via a registry (ADR-0023)."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    tool_id: UUID
    app_version: str
    ui_mode: CuratedAppUiMode = CuratedAppUiMode.GENERIC_OK
    title: str
    summary: str | None = None
    min_role: Role = Role.USER
    public_access_profile: CuratedAppPublicAccessProfile = (
        CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY
    )
    public_capabilities: list[CuratedAppPublicCapability] = Field(default_factory=list)
    default_favorite: bool = False
    placements: list[CuratedAppPlacement]

    @field_validator("app_id", "app_version", "title")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("summary")
    @classmethod
    def _normalize_optional_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None

    @field_validator("placements")
    @classmethod
    def _validate_placements(cls, value: list[CuratedAppPlacement]) -> list[CuratedAppPlacement]:
        if not value:
            raise ValueError("placements is required")
        return value

    @field_validator("public_capabilities")
    @classmethod
    def _validate_public_capabilities(
        cls, value: list[CuratedAppPublicCapability]
    ) -> list[CuratedAppPublicCapability]:
        seen_scopes: set[str] = set()
        for capability in value:
            if capability.scope in seen_scopes:
                raise ValueError("public capability scopes must be unique")
            seen_scopes.add(capability.scope)
        return value

    @model_validator(mode="after")
    def _validate_tool_id_matches_app_id(self) -> CuratedAppDefinition:
        expected = curated_app_tool_id(app_id=self.app_id)
        if self.tool_id != expected:
            raise ValueError("tool_id must be derived deterministically from app_id")
        return self

    def matches_placement(self, *, profession_slug: str, category_slug: str) -> bool:
        normalized_profession = profession_slug.strip()
        normalized_category = category_slug.strip()
        return any(
            p.profession_slug == normalized_profession and p.category_slug == normalized_category
            for p in self.placements
        )

    @property
    def supports_public_access(self) -> bool:
        return self.public_access_profile is not CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY

    def get_public_capability(self, *, scope: str) -> CuratedAppPublicCapability | None:
        normalized_scope = scope.strip()
        for capability in self.public_capabilities:
            if capability.scope == normalized_scope:
                return capability
        return None

    def supports_public_capability(self, *, scope: str) -> bool:
        return self.get_public_capability(scope=scope) is not None
