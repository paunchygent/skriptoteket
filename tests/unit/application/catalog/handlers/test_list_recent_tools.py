from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.catalog.handlers.list_recent_tools import ListRecentToolsHandler
from skriptoteket.application.catalog.queries import CatalogItemKind, ListRecentToolsQuery
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import RunSourceKind
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from skriptoteket.protocols.scripting import RecentRunRow, ToolRunRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


def _make_app(
    *,
    app_id: str,
    min_role: Role,
) -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="1.0.0",
        title="Counter",
        summary="Demo app",
        min_role=min_role,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="svenska")],
    )


@pytest.mark.asyncio
async def test_list_recent_tools_preserves_order_and_sets_favorites(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool_a = make_tool(slug="alpha", title="Alpha", is_published=True, now=now)
    tool_b = make_tool(slug="beta", title="Beta", is_published=True, now=now)
    app = _make_app(app_id="demo.counter", min_role=Role.USER)

    rows = [
        RecentRunRow(
            source_kind=RunSourceKind.TOOL_VERSION,
            tool_id=tool_b.id,
            curated_app_id=None,
            last_used_at=now + timedelta(minutes=3),
        ),
        RecentRunRow(
            source_kind=RunSourceKind.CURATED_APP,
            tool_id=app.tool_id,
            curated_app_id=app.app_id,
            last_used_at=now + timedelta(minutes=2),
        ),
        RecentRunRow(
            source_kind=RunSourceKind.TOOL_VERSION,
            tool_id=tool_a.id,
            curated_app_id=None,
            last_used_at=now + timedelta(minutes=1),
        ),
    ]

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.list_recent_tools_for_user.return_value = rows

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.list_by_ids.return_value = [tool_a, tool_b]

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_app_id.return_value = app

    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    favorites.list_favorites_for_tools.return_value = {tool_b.id}
    favorites.list_favorites_for_apps.return_value = {app.app_id}

    handler = ListRecentToolsHandler(
        runs=runs,
        tools=tools,
        curated_apps=curated_apps,
        favorites=favorites,
    )

    result = await handler.handle(actor=actor, query=ListRecentToolsQuery(limit=10))

    runs.list_recent_tools_for_user.assert_awaited_once_with(user_id=actor.id, limit=30)
    tools.list_by_ids.assert_awaited_once_with(tool_ids=[tool_b.id, tool_a.id])
    favorites.list_favorites_for_tools.assert_awaited_once_with(
        user_id=actor.id,
        tool_ids=[tool_b.id, tool_a.id],
    )
    favorites.list_favorites_for_apps.assert_awaited_once_with(
        user_id=actor.id,
        app_ids=[app.app_id],
    )

    assert [
        (item.kind, item.title, item.is_favorite, item.last_used_at) for item in result.items
    ] == [
        (CatalogItemKind.TOOL, "Beta", True, rows[0].last_used_at),
        (CatalogItemKind.CURATED_APP, "Counter", True, rows[1].last_used_at),
        (CatalogItemKind.TOOL, "Alpha", False, rows[2].last_used_at),
    ]


@pytest.mark.asyncio
async def test_list_recent_tools_filters_unpublished_and_role_blocked(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    published_tool = make_tool(slug="alpha", title="Alpha", is_published=True, now=now)
    unpublished_tool = make_tool(slug="beta", title="Beta", is_published=False, now=now)
    blocked_app = _make_app(app_id="demo.blocked", min_role=Role.ADMIN)

    rows = [
        RecentRunRow(
            source_kind=RunSourceKind.TOOL_VERSION,
            tool_id=unpublished_tool.id,
            curated_app_id=None,
            last_used_at=now + timedelta(minutes=3),
        ),
        RecentRunRow(
            source_kind=RunSourceKind.CURATED_APP,
            tool_id=blocked_app.tool_id,
            curated_app_id=blocked_app.app_id,
            last_used_at=now + timedelta(minutes=2),
        ),
        RecentRunRow(
            source_kind=RunSourceKind.TOOL_VERSION,
            tool_id=published_tool.id,
            curated_app_id=None,
            last_used_at=now + timedelta(minutes=1),
        ),
    ]

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.list_recent_tools_for_user.return_value = rows

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.list_by_ids.return_value = [unpublished_tool, published_tool]

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_app_id.return_value = blocked_app

    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    favorites.list_favorites_for_tools.return_value = set()
    favorites.list_favorites_for_apps.return_value = set()

    handler = ListRecentToolsHandler(
        runs=runs,
        tools=tools,
        curated_apps=curated_apps,
        favorites=favorites,
    )

    result = await handler.handle(actor=actor, query=ListRecentToolsQuery(limit=5))

    assert [(item.kind, item.title) for item in result.items] == [(CatalogItemKind.TOOL, "Alpha")]
    favorites.list_favorites_for_tools.assert_awaited_once_with(
        user_id=actor.id,
        tool_ids=[published_tool.id],
    )
    favorites.list_favorites_for_apps.assert_awaited_once_with(
        user_id=actor.id,
        app_ids=[],
    )


@pytest.mark.asyncio
async def test_list_recent_tools_returns_empty_when_no_runs(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.list_recent_tools_for_user.return_value = []

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)

    handler = ListRecentToolsHandler(
        runs=runs,
        tools=tools,
        curated_apps=curated_apps,
        favorites=favorites,
    )

    result = await handler.handle(actor=actor, query=ListRecentToolsQuery(limit=10))

    assert result.items == []
    tools.list_by_ids.assert_not_awaited()
    favorites.list_favorites_for_tools.assert_not_awaited()
    favorites.list_favorites_for_apps.assert_not_awaited()
