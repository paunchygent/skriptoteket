from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.favorites.commands import AddFavoriteCommand
from skriptoteket.application.favorites.handlers.add_favorite import AddFavoriteHandler
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_add_favorite_adds_published_tool(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=True)

    uow = FakeUow()
    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None

    handler = AddFavoriteHandler(
        uow=uow,
        favorites=favorites,
        tools=tools,
        curated_apps=curated_apps,
    )

    result = await handler.handle(
        actor=actor,
        command=AddFavoriteCommand(catalog_item_id=tool.id),
    )

    assert result.id == tool.id
    assert result.is_favorite is True
    assert uow.entered is True
    assert uow.exited is True
    favorites.add_tool.assert_awaited_once_with(user_id=actor.id, tool_id=tool.id)


@pytest.mark.asyncio
async def test_add_favorite_adds_curated_app_when_allowed(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    app_id = "demo.counter"
    app = CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="test",
        title="Counter",
        summary=None,
        min_role=Role.ADMIN,
        placements=[CuratedAppPlacement(profession_slug="math", category_slug="calc")],
    )

    uow = FakeUow()
    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = app

    handler = AddFavoriteHandler(
        uow=uow,
        favorites=favorites,
        tools=tools,
        curated_apps=curated_apps,
    )

    result = await handler.handle(
        actor=actor,
        command=AddFavoriteCommand(catalog_item_id=app.tool_id),
    )

    assert result.id == app.tool_id
    assert result.is_favorite is True
    favorites.add_app.assert_awaited_once_with(user_id=actor.id, app_id=app.app_id)


@pytest.mark.asyncio
async def test_add_favorite_raises_when_unpublished_tool(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=False)

    uow = FakeUow()
    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None

    handler = AddFavoriteHandler(
        uow=uow,
        favorites=favorites,
        tools=tools,
        curated_apps=curated_apps,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AddFavoriteCommand(catalog_item_id=tool.id),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    favorites.add_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_favorite_raises_when_curated_app_not_allowed() -> None:
    actor = make_user(role=Role.USER)
    app_id = "demo.admin"
    app = CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="test",
        title="Admin only",
        summary=None,
        min_role=Role.ADMIN,
        placements=[CuratedAppPlacement(profession_slug="math", category_slug="calc")],
    )

    uow = FakeUow()
    favorites = AsyncMock(spec=FavoritesRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = app

    handler = AddFavoriteHandler(
        uow=uow,
        favorites=favorites,
        tools=tools,
        curated_apps=curated_apps,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AddFavoriteCommand(catalog_item_id=app.tool_id),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    favorites.add_app.assert_not_awaited()
