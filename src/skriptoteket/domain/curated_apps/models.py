from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from skriptoteket.domain.identity.models import Role

_CURATED_APPS_NAMESPACE = uuid5(NAMESPACE_URL, "skriptoteket.curated_apps")


def curated_app_tool_id(*, app_id: str) -> UUID:
    normalized = app_id.strip()
    if not normalized:
        raise ValueError("app_id is required")
    return uuid5(_CURATED_APPS_NAMESPACE, normalized)


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


class CuratedAppDefinition(BaseModel):
    """Curated app metadata discovered via a registry (ADR-0023)."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    tool_id: UUID
    app_version: str
    title: str
    summary: str | None = None
    min_role: Role = Role.USER
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
