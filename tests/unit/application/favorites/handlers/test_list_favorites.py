from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.favorites.handlers.list_favorites import ListFavoritesHandler
from skriptoteket.application.favorites.queries import ListFavoritesQuery
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind, FavoriteCatalogRef
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_list_favorites_filters_unpublished_and_role_gated(now: datetime) -> None:
    actor = make_user(role=Role.USER)

    published_tool = make_tool(now=now, is_published=True)
    unpublished_tool = make_tool(now=now, is_published=False)

    allowed_app_id = "demo.allowed"
    allowed_app = CuratedAppDefinition(
        app_id=allowed_app_id,
        tool_id=curated_app_tool_id(app_id=allowed_app_id),
        app_version="test",
        title="Allowed",
        summary=None,
        min_role=Role.USER,
        placements=[CuratedAppPlacement(profession_slug="math", category_slug="calc")],
    )
    blocked_app_id = "demo.blocked"
    blocked_app = CuratedAppDefinition(
        app_id=blocked_app_id,
        tool_id=curated_app_tool_id(app_id=blocked_app_id),
        app_version="test",
        title="Blocked",
        summary=None,
        min_role=Role.ADMIN,
        placements=[CuratedAppPlacement(profession_slug="math", category_slug="calc")],
    )

    refs = [
        FavoriteCatalogRef(
            kind=FavoriteCatalogItemKind.TOOL,
            tool_id=published_tool.id,
            created_at=now,
        ),
        FavoriteCatalogRef(
            kind=FavoriteCatalogItemKind.TOOL,
            tool_id=unpublished_tool.id,
            created_at=now,
        ),
        FavoriteCatalogRef(
            kind=FavoriteCatalogItemKind.CURATED_APP,
            app_id=allowed_app.app_id,
            created_at=now,
        ),
        FavoriteCatalogRef(
            kind=FavoriteCatalogItemKind.CURATED_APP,
            app_id=blocked_app.app_id,
            created_at=now,
        ),
    ]

    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    favorites.list_catalog_refs_for_user.return_value = refs

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.side_effect = lambda *, tool_id: {
        published_tool.id: published_tool,
        unpublished_tool.id: unpublished_tool,
    }.get(tool_id)

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_app_id.side_effect = lambda *, app_id: {
        allowed_app_id: allowed_app,
        blocked_app_id: blocked_app,
    }.get(app_id)

    handler = ListFavoritesHandler(
        favorites=favorites,
        tools=tools,
        curated_apps=curated_apps,
    )

    result = await handler.handle(actor=actor, query=ListFavoritesQuery())

    assert [item.kind for item in result.items] == [
        FavoriteCatalogItemKind.TOOL,
        FavoriteCatalogItemKind.CURATED_APP,
    ]
    assert result.items[0].id == published_tool.id
    assert result.items[1].id == allowed_app.tool_id


@pytest.mark.asyncio
async def test_list_favorites_respects_limit_and_overfetch(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=True)

    refs = [
        FavoriteCatalogRef(
            kind=FavoriteCatalogItemKind.TOOL,
            tool_id=tool.id,
            created_at=now,
        ),
        FavoriteCatalogRef(
            kind=FavoriteCatalogItemKind.TOOL,
            tool_id=uuid4(),
            created_at=now,
        ),
    ]

    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    favorites.list_catalog_refs_for_user.return_value = refs

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.side_effect = lambda *, tool_id: tool if tool_id == tool.id else None

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_app_id.return_value = None

    handler = ListFavoritesHandler(
        favorites=favorites,
        tools=tools,
        curated_apps=curated_apps,
    )

    result = await handler.handle(actor=actor, query=ListFavoritesQuery(limit=1))

    assert len(result.items) == 1
    favorites.list_catalog_refs_for_user.assert_awaited_once_with(user_id=actor.id, limit=6)
