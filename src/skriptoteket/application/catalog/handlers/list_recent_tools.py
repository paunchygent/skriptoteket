from __future__ import annotations

from uuid import UUID

from skriptoteket.application.catalog.queries import (
    CatalogItemKind,
    ListRecentToolsQuery,
    ListRecentToolsResult,
    RecentCatalogItem,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import has_at_least_role
from skriptoteket.domain.scripting.models import RunSourceKind
from skriptoteket.protocols.catalog import ListRecentToolsHandlerProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol

_OVERFETCH_FACTOR = 3
_OVERFETCH_BUFFER = 5


def _compute_fetch_limit(limit: int) -> int:
    return max(limit * _OVERFETCH_FACTOR, limit + _OVERFETCH_BUFFER)


class ListRecentToolsHandler(ListRecentToolsHandlerProtocol):
    def __init__(
        self,
        *,
        runs: ToolRunRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        favorites: FavoritesRepositoryProtocol,
    ) -> None:
        self._runs = runs
        self._tools = tools
        self._curated_apps = curated_apps
        self._favorites = favorites

    async def handle(self, *, actor: User, query: ListRecentToolsQuery) -> ListRecentToolsResult:
        fetch_limit = _compute_fetch_limit(query.limit)
        rows = await self._runs.list_recent_tools_for_user(
            user_id=actor.id,
            limit=fetch_limit,
        )

        if not rows:
            return ListRecentToolsResult(items=[])

        tool_ids = [row.tool_id for row in rows if row.source_kind is RunSourceKind.TOOL_VERSION]
        tools = await self._tools.list_by_ids(tool_ids=tool_ids)
        tool_lookup = {tool.id: tool for tool in tools if tool.is_published}

        items: list[RecentCatalogItem] = []
        tool_refs: list[UUID] = []
        app_refs: list[str] = []

        for row in rows:
            if row.source_kind is RunSourceKind.TOOL_VERSION:
                tool = tool_lookup.get(row.tool_id)
                if tool is None:
                    continue
                items.append(
                    RecentCatalogItem(
                        kind=CatalogItemKind.TOOL,
                        id=tool.id,
                        slug=tool.slug,
                        title=tool.title,
                        summary=tool.summary,
                        is_favorite=False,
                        last_used_at=row.last_used_at,
                    )
                )
                tool_refs.append(tool.id)
            else:
                if not row.curated_app_id:
                    continue
                app = self._curated_apps.get_by_app_id(app_id=row.curated_app_id)
                if app is None or not has_at_least_role(user=actor, role=app.min_role):
                    continue
                items.append(
                    RecentCatalogItem(
                        kind=CatalogItemKind.CURATED_APP,
                        id=app.tool_id,
                        app_id=app.app_id,
                        title=app.title,
                        summary=app.summary,
                        is_favorite=False,
                        last_used_at=row.last_used_at,
                    )
                )
                app_refs.append(app.app_id)

            if len(items) >= query.limit:
                break

        if not items:
            return ListRecentToolsResult(items=[])

        favorite_tool_ids = await self._favorites.list_favorites_for_tools(
            user_id=actor.id,
            tool_ids=tool_refs,
        )
        favorite_app_ids = await self._favorites.list_favorites_for_apps(
            user_id=actor.id,
            app_ids=app_refs,
        )

        resolved_items: list[RecentCatalogItem] = []
        for item in items:
            if item.kind is CatalogItemKind.TOOL:
                is_favorite = item.id in favorite_tool_ids
            else:
                is_favorite = (item.app_id or "") in favorite_app_ids
            resolved_items.append(item.model_copy(update={"is_favorite": is_favorite}))

        return ListRecentToolsResult(items=resolved_items)
