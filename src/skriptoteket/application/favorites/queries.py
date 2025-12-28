from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind


class FavoriteCatalogItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: FavoriteCatalogItemKind
    id: UUID
    slug: str | None = None
    app_id: str | None = None
    title: str
    summary: str | None = None
    is_favorite: bool = True


class ListFavoritesQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    limit: int | None = None


class ListFavoritesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[FavoriteCatalogItem]
