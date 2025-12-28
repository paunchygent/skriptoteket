from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from skriptoteket.application.catalog.queries import (
    CatalogItem,
    CatalogItemKind,
    ListAllToolsQuery,
    ListAllToolsResult,
)
from skriptoteket.domain.catalog.models import Category, Profession
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import (
    CatalogFilterProtocol,
    CategoryRepositoryProtocol,
    ListAllToolsHandlerProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol


def _normalize_slug_list(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    normalized = [value.strip().lower() for value in values if value and value.strip()]
    return normalized or None


def _normalize_search_term(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _resolve_ids(items: Iterable[Profession | Category], slugs: list[str] | None) -> list[UUID]:
    if not slugs:
        return []
    slug_map = {item.slug: item.id for item in items}
    return [slug_map[slug] for slug in slugs if slug in slug_map]


class ListAllToolsHandler(ListAllToolsHandlerProtocol):
    def __init__(
        self,
        *,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        favorites: FavoritesRepositoryProtocol,
        catalog_filter: CatalogFilterProtocol,
    ) -> None:
        self._professions = professions
        self._categories = categories
        self._tools = tools
        self._curated_apps = curated_apps
        self._favorites = favorites
        self._catalog_filter = catalog_filter

    async def handle(self, *, actor: User, query: ListAllToolsQuery) -> ListAllToolsResult:
        professions = await self._professions.list_all()
        categories = await self._categories.list_all()

        profession_slugs = _normalize_slug_list(query.profession_slugs)
        category_slugs = _normalize_slug_list(query.category_slugs)
        search_term = _normalize_search_term(query.search_term)

        professions_requested = profession_slugs is not None
        categories_requested = category_slugs is not None

        profession_ids = _resolve_ids(professions, profession_slugs)
        if professions_requested and not profession_ids:
            return ListAllToolsResult(items=[], professions=professions, categories=categories)

        category_ids = _resolve_ids(categories, category_slugs)
        if categories_requested and not category_ids:
            return ListAllToolsResult(items=[], professions=professions, categories=categories)

        tools = await self._tools.list_published_filtered(
            profession_ids=profession_ids if professions_requested else None,
            category_ids=category_ids if categories_requested else None,
            search_term=search_term,
        )

        curated_apps = self._catalog_filter.filter_curated_apps(
            apps=self._curated_apps.list_all(),
            actor=actor,
            profession_slugs=profession_slugs,
            category_slugs=category_slugs,
            search_term=search_term,
        )

        favorite_tool_ids = await self._favorites.list_favorites_for_tools(
            user_id=actor.id,
            tool_ids=[tool.id for tool in tools],
        )
        favorite_app_ids = await self._favorites.list_favorites_for_apps(
            user_id=actor.id,
            app_ids=[app.app_id for app in curated_apps],
        )

        items: list[CatalogItem] = [
            CatalogItem(
                kind=CatalogItemKind.TOOL,
                id=tool.id,
                slug=tool.slug,
                title=tool.title,
                summary=tool.summary,
                is_favorite=tool.id in favorite_tool_ids,
            )
            for tool in tools
        ] + [
            CatalogItem(
                kind=CatalogItemKind.CURATED_APP,
                id=app.tool_id,
                app_id=app.app_id,
                title=app.title,
                summary=app.summary,
                is_favorite=app.app_id in favorite_app_ids,
            )
            for app in curated_apps
        ]

        items.sort(key=lambda item: (item.title.casefold(), item.slug or item.app_id or ""))
        return ListAllToolsResult(
            items=items,
            professions=professions,
            categories=categories,
        )
