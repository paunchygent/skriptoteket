from __future__ import annotations

from skriptoteket.application.favorites.queries import (
    FavoriteCatalogItem,
    ListFavoritesQuery,
    ListFavoritesResult,
)
from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import has_at_least_role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import (
    FavoritesRepositoryProtocol,
    ListFavoritesHandlerProtocol,
)

_OVERFETCH_FACTOR = 3
_OVERFETCH_BUFFER = 5


def _compute_fetch_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    return max(limit * _OVERFETCH_FACTOR, limit + _OVERFETCH_BUFFER)


class ListFavoritesHandler(ListFavoritesHandlerProtocol):
    def __init__(
        self,
        *,
        favorites: FavoritesRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> None:
        self._favorites = favorites
        self._tools = tools
        self._curated_apps = curated_apps

    async def handle(self, *, actor: User, query: ListFavoritesQuery) -> ListFavoritesResult:
        fetch_limit = _compute_fetch_limit(query.limit)
        refs = await self._favorites.list_catalog_refs_for_user(
            user_id=actor.id,
            limit=fetch_limit,
        )

        items: list[FavoriteCatalogItem] = []
        for ref in refs:
            if ref.kind is FavoriteCatalogItemKind.TOOL:
                if ref.tool_id is None:
                    continue
                tool = await self._tools.get_by_id(tool_id=ref.tool_id)
                if tool is None or not tool.is_published:
                    continue
                items.append(
                    FavoriteCatalogItem(
                        kind=FavoriteCatalogItemKind.TOOL,
                        id=tool.id,
                        slug=tool.slug,
                        title=tool.title,
                        summary=tool.summary,
                        is_favorite=True,
                    )
                )
            else:
                if not ref.app_id:
                    continue
                app = self._curated_apps.get_by_app_id(app_id=ref.app_id)
                if app is None or not has_at_least_role(user=actor, role=app.min_role):
                    continue
                items.append(
                    FavoriteCatalogItem(
                        kind=FavoriteCatalogItemKind.CURATED_APP,
                        id=app.tool_id,
                        app_id=app.app_id,
                        title=app.title,
                        summary=app.summary,
                        is_favorite=True,
                    )
                )

            if query.limit is not None and len(items) >= query.limit:
                break

        return ListFavoritesResult(items=items)
