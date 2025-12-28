from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.favorites.commands import (
    AddFavoriteCommand,
    FavoriteStatusResult,
    RemoveFavoriteCommand,
)
from skriptoteket.application.favorites.queries import (
    ListFavoritesQuery,
    ListFavoritesResult,
)
from skriptoteket.domain.favorites.models import (
    FavoriteCatalogRef,
    UserFavoriteCuratedApp,
    UserFavoriteTool,
)
from skriptoteket.domain.identity.models import User


class FavoritesRepositoryProtocol(Protocol):
    async def add_tool(self, *, user_id: UUID, tool_id: UUID) -> UserFavoriteTool: ...
    async def remove_tool(self, *, user_id: UUID, tool_id: UUID) -> None: ...
    async def is_favorite_tool(self, *, user_id: UUID, tool_id: UUID) -> bool: ...
    async def list_tool_ids_for_user(
        self, *, user_id: UUID, limit: int | None = None
    ) -> list[UUID]: ...
    async def list_favorites_for_tools(
        self, *, user_id: UUID, tool_ids: list[UUID]
    ) -> set[UUID]: ...
    async def list_catalog_refs_for_user(
        self, *, user_id: UUID, limit: int | None = None
    ) -> list[FavoriteCatalogRef]: ...

    async def add_app(self, *, user_id: UUID, app_id: str) -> UserFavoriteCuratedApp: ...
    async def remove_app(self, *, user_id: UUID, app_id: str) -> None: ...
    async def is_favorite_app(self, *, user_id: UUID, app_id: str) -> bool: ...
    async def list_app_ids_for_user(
        self, *, user_id: UUID, limit: int | None = None
    ) -> list[str]: ...
    async def list_favorites_for_apps(self, *, user_id: UUID, app_ids: list[str]) -> set[str]: ...


class AddFavoriteHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, command: AddFavoriteCommand) -> FavoriteStatusResult: ...


class RemoveFavoriteHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, command: RemoveFavoriteCommand
    ) -> FavoriteStatusResult: ...


class ListFavoritesHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, query: ListFavoritesQuery) -> ListFavoritesResult: ...
