from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.catalog.handlers.list_all_tools import ListAllToolsHandler
from skriptoteket.application.catalog.queries import CatalogItemKind, ListAllToolsQuery
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import (
    CatalogFilterProtocol,
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_category, make_profession, make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_list_all_tools_ignores_unknown_slugs_and_sets_favorites(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    profession = make_profession(slug="larare", now=now)
    category = make_category(slug="svenska", now=now)

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.list_all.return_value = [profession]

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.list_all.return_value = [category]

    tool = make_tool(slug="alpha", title="Alpha", now=now, is_published=True)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.list_published_filtered.return_value = [tool]

    app_id = "demo.app"
    curated_app = CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="test",
        title="Beta",
        summary=None,
        min_role=Role.USER,
        placements=[
            CuratedAppPlacement(
                profession_slug=profession.slug,
                category_slug=category.slug,
            )
        ],
    )
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.list_all.return_value = [curated_app]

    catalog_filter = Mock(spec=CatalogFilterProtocol)
    catalog_filter.filter_curated_apps.return_value = [curated_app]

    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    favorites.list_favorites_for_tools.return_value = {tool.id}
    favorites.list_favorites_for_apps.return_value = set()

    handler = ListAllToolsHandler(
        professions=professions,
        categories=categories,
        tools=tools,
        curated_apps=curated_apps,
        favorites=favorites,
        catalog_filter=catalog_filter,
    )

    result = await handler.handle(
        actor=actor,
        query=ListAllToolsQuery(
            profession_slugs=["larare", "nope"],
            category_slugs=["svenska"],
            search_term="Test",
        ),
    )

    tools.list_published_filtered.assert_awaited_once_with(
        profession_ids=[profession.id],
        category_ids=[category.id],
        search_term="Test",
    )
    catalog_filter.filter_curated_apps.assert_called_once_with(
        apps=[curated_app],
        actor=actor,
        profession_slugs=["larare", "nope"],
        category_slugs=["svenska"],
        search_term="Test",
    )

    assert result.professions == [profession]
    assert result.categories == [category]
    assert [(item.kind, item.title, item.is_favorite) for item in result.items] == [
        (CatalogItemKind.TOOL, "Alpha", True),
        (CatalogItemKind.CURATED_APP, "Beta", False),
    ]


@pytest.mark.asyncio
async def test_list_all_tools_returns_empty_when_profession_param_unresolvable(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    profession = make_profession(slug="larare", now=now)
    category = make_category(slug="svenska", now=now)

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.list_all.return_value = [profession]

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.list_all.return_value = [category]

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    catalog_filter = Mock(spec=CatalogFilterProtocol)

    handler = ListAllToolsHandler(
        professions=professions,
        categories=categories,
        tools=tools,
        curated_apps=curated_apps,
        favorites=favorites,
        catalog_filter=catalog_filter,
    )

    result = await handler.handle(
        actor=actor,
        query=ListAllToolsQuery(
            profession_slugs=["missing"],
            category_slugs=None,
            search_term=None,
        ),
    )

    tools.list_published_filtered.assert_not_awaited()
    catalog_filter.filter_curated_apps.assert_not_called()
    favorites.list_favorites_for_tools.assert_not_awaited()
    favorites.list_favorites_for_apps.assert_not_awaited()

    assert result.items == []
    assert result.professions == [profession]
    assert result.categories == [category]
