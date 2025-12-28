"""Favorites domain provider: add/remove/list handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.favorites.handlers.add_favorite import AddFavoriteHandler
from skriptoteket.application.favorites.handlers.list_favorites import ListFavoritesHandler
from skriptoteket.application.favorites.handlers.remove_favorite import RemoveFavoriteHandler
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import (
    AddFavoriteHandlerProtocol,
    FavoritesRepositoryProtocol,
    ListFavoritesHandlerProtocol,
    RemoveFavoriteHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class FavoritesProvider(Provider):
    """Provides favorites handlers."""

    @provide(scope=Scope.REQUEST)
    def add_favorite_handler(
        self,
        uow: UnitOfWorkProtocol,
        favorites: FavoritesRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> AddFavoriteHandlerProtocol:
        return AddFavoriteHandler(
            uow=uow,
            favorites=favorites,
            tools=tools,
            curated_apps=curated_apps,
        )

    @provide(scope=Scope.REQUEST)
    def remove_favorite_handler(
        self,
        uow: UnitOfWorkProtocol,
        favorites: FavoritesRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> RemoveFavoriteHandlerProtocol:
        return RemoveFavoriteHandler(
            uow=uow,
            favorites=favorites,
            tools=tools,
            curated_apps=curated_apps,
        )

    @provide(scope=Scope.REQUEST)
    def list_favorites_handler(
        self,
        favorites: FavoritesRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> ListFavoritesHandlerProtocol:
        return ListFavoritesHandler(
            favorites=favorites,
            tools=tools,
            curated_apps=curated_apps,
        )
