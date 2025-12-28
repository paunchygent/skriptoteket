from __future__ import annotations

from skriptoteket.application.favorites.commands import FavoriteStatusResult, RemoveFavoriteCommand
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import has_at_least_role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import (
    FavoritesRepositoryProtocol,
    RemoveFavoriteHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RemoveFavoriteHandler(RemoveFavoriteHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        favorites: FavoritesRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> None:
        self._uow = uow
        self._favorites = favorites
        self._tools = tools
        self._curated_apps = curated_apps

    async def handle(self, *, actor: User, command: RemoveFavoriteCommand) -> FavoriteStatusResult:
        tool = await self._tools.get_by_id(tool_id=command.catalog_item_id)
        if tool is not None and tool.is_published:
            async with self._uow:
                await self._favorites.remove_tool(user_id=actor.id, tool_id=tool.id)
            return FavoriteStatusResult(id=tool.id, is_favorite=False)

        app = self._curated_apps.get_by_tool_id(tool_id=command.catalog_item_id)
        if app is not None and has_at_least_role(user=actor, role=app.min_role):
            async with self._uow:
                await self._favorites.remove_app(user_id=actor.id, app_id=app.app_id)
            return FavoriteStatusResult(id=app.tool_id, is_favorite=False)

        raise not_found("catalog_item", str(command.catalog_item_id))
