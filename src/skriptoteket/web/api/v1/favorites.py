from __future__ import annotations

from typing import Literal
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.favorites.commands import AddFavoriteCommand, RemoveFavoriteCommand
from skriptoteket.application.favorites.queries import ListFavoritesQuery
from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.favorites import (
    AddFavoriteHandlerProtocol,
    ListFavoritesHandlerProtocol,
    RemoveFavoriteHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api

router = APIRouter(prefix="/api/v1/favorites", tags=["favorites"])


class FavoriteStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    is_favorite: bool


class FavoriteToolItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["tool"]
    id: UUID
    slug: str
    title: str
    summary: str | None
    is_favorite: bool


class FavoriteCuratedAppItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["curated_app"]
    id: UUID
    app_id: str
    title: str
    summary: str | None
    is_favorite: bool


class ListFavoritesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[FavoriteToolItem | FavoriteCuratedAppItem]


@router.post("/{catalog_item_id}", response_model=FavoriteStatusResponse)
@inject
async def add_favorite(
    catalog_item_id: UUID,
    handler: FromDishka[AddFavoriteHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> FavoriteStatusResponse:
    result = await handler.handle(
        actor=user,
        command=AddFavoriteCommand(catalog_item_id=catalog_item_id),
    )
    return FavoriteStatusResponse(id=result.id, is_favorite=result.is_favorite)


@router.delete("/{catalog_item_id}", response_model=FavoriteStatusResponse)
@inject
async def remove_favorite(
    catalog_item_id: UUID,
    handler: FromDishka[RemoveFavoriteHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> FavoriteStatusResponse:
    result = await handler.handle(
        actor=user,
        command=RemoveFavoriteCommand(catalog_item_id=catalog_item_id),
    )
    return FavoriteStatusResponse(id=result.id, is_favorite=result.is_favorite)


@router.get("", response_model=ListFavoritesResponse)
@inject
async def list_favorites(
    handler: FromDishka[ListFavoritesHandlerProtocol],
    user: User = Depends(require_user_api),
    limit: int | None = None,
) -> ListFavoritesResponse:
    result = await handler.handle(actor=user, query=ListFavoritesQuery(limit=limit))
    items: list[FavoriteToolItem | FavoriteCuratedAppItem] = []
    for item in result.items:
        if item.kind is FavoriteCatalogItemKind.TOOL:
            items.append(
                FavoriteToolItem(
                    kind="tool",
                    id=item.id,
                    slug=item.slug,
                    title=item.title,
                    summary=item.summary,
                    is_favorite=item.is_favorite,
                )
            )
        else:
            items.append(
                FavoriteCuratedAppItem(
                    kind="curated_app",
                    id=item.id,
                    app_id=item.app_id,
                    title=item.title,
                    summary=item.summary,
                    is_favorite=item.is_favorite,
                )
            )
    return ListFavoritesResponse(items=items)
