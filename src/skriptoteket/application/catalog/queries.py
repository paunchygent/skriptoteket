from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.catalog.models import Category, Profession, Tool, ToolVersionStats
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.identity.models import User


class ListProfessionsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListProfessionsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    professions: list[Profession]


class ListAllCategoriesQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListAllCategoriesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    categories: list[Category]


class ListCategoriesForProfessionQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_slug: str


class ListCategoriesForProfessionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession: Profession
    categories: list[Category]


class ListToolsByTagsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_slug: str
    category_slug: str


class ListToolsByTagsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession: Profession
    category: Category
    tools: list[Tool]
    curated_apps: list[CuratedAppDefinition]


class CatalogItemKind(StrEnum):
    TOOL = "tool"
    CURATED_APP = "curated_app"


class CatalogItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: CatalogItemKind
    id: UUID
    slug: str | None = None
    app_id: str | None = None
    title: str
    summary: str | None = None
    is_favorite: bool = False


class ListRecentToolsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    limit: int = 10


class RecentCatalogItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: CatalogItemKind
    id: UUID
    slug: str | None = None
    app_id: str | None = None
    title: str
    summary: str | None = None
    is_favorite: bool = False
    last_used_at: datetime


class ListRecentToolsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[RecentCatalogItem]


class ListAllToolsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_slugs: list[str] | None = None
    category_slugs: list[str] | None = None
    search_term: str | None = None


class ListAllToolsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CatalogItem]
    professions: list[Profession]
    categories: list[Category]


class ListToolsForAdminQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListToolsForAdminResult(BaseModel):
    """Result with tools and version statistics for admin listing (ADR-0033)."""

    model_config = ConfigDict(frozen=True)

    tools: list[Tool]
    version_stats: dict[UUID, ToolVersionStats]


class ListMaintainersQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class ListMaintainersResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    owner_user_id: UUID
    maintainers: list[User]


class ListToolsForContributorQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListToolsForContributorResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tools: list[Tool]


class ListToolTaxonomyQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class ListToolTaxonomyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    profession_ids: list[UUID]
    category_ids: list[UUID]
