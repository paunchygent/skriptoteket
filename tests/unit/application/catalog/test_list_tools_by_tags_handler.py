from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.catalog.handlers.list_tools_by_tags import ListToolsByTagsHandler
from skriptoteket.application.catalog.queries import ListToolsByTagsQuery
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from tests.fixtures.catalog_fixtures import make_category, make_profession, make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_list_tools_by_tags_returns_tools(now: datetime) -> None:
    actor = make_user()
    profession = make_profession(now=now)
    category = make_category(now=now)
    tools_list = [
        make_tool(slug="a", title="A", now=now),
        make_tool(slug="b", title="B", now=now),
    ]

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = profession

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.get_for_profession_by_slug.return_value = category

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.list_by_tags.return_value = tools_list

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.list_all.return_value = []

    handler = ListToolsByTagsHandler(
        professions=professions,
        categories=categories,
        tools=tools,
        curated_apps=curated_apps,
    )
    result = await handler.handle(
        actor=actor,
        query=ListToolsByTagsQuery(profession_slug=profession.slug, category_slug=category.slug),
    )

    assert result.profession == profession
    assert result.category == category
    assert result.tools == tools_list
    assert result.curated_apps == []
    tools.list_by_tags.assert_awaited_once_with(
        profession_id=profession.id,
        category_id=category.id,
    )


@pytest.mark.asyncio
async def test_list_tools_by_tags_raises_when_profession_missing() -> None:
    actor = make_user()
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = None

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.list_all.return_value = []

    handler = ListToolsByTagsHandler(
        professions=professions,
        categories=categories,
        tools=tools,
        curated_apps=curated_apps,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            query=ListToolsByTagsQuery(profession_slug="nope", category_slug="x"),
        )

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    categories.get_for_profession_by_slug.assert_not_awaited()
    tools.list_by_tags.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_tools_by_tags_raises_when_category_not_in_profession(now: datetime) -> None:
    actor = make_user()
    profession = make_profession(now=now)

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = profession

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.get_for_profession_by_slug.return_value = None

    tools = AsyncMock(spec=ToolRepositoryProtocol)

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.list_all.return_value = []

    handler = ListToolsByTagsHandler(
        professions=professions,
        categories=categories,
        tools=tools,
        curated_apps=curated_apps,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            query=ListToolsByTagsQuery(profession_slug=profession.slug, category_slug="nope"),
        )

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    tools.list_by_tags.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_tools_by_tags_includes_curated_apps_role_gated(now: datetime) -> None:
    profession = make_profession(now=now)
    category = make_category(now=now)

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = profession

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.get_for_profession_by_slug.return_value = category

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.list_by_tags.return_value = []

    app_id = "demo.role-gated"
    app = CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="test",
        title="Admin-only app",
        summary=None,
        min_role=Role.ADMIN,
        placements=[
            CuratedAppPlacement(
                profession_slug=profession.slug,
                category_slug=category.slug,
            )
        ],
    )

    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.list_all.return_value = [app]

    handler = ListToolsByTagsHandler(
        professions=professions,
        categories=categories,
        tools=tools,
        curated_apps=curated_apps,
    )

    user_actor = make_user(role=Role.USER)
    user_result = await handler.handle(
        actor=user_actor,
        query=ListToolsByTagsQuery(profession_slug=profession.slug, category_slug=category.slug),
    )
    assert user_result.curated_apps == []

    admin_actor = make_user(role=Role.ADMIN)
    admin_result = await handler.handle(
        actor=admin_actor,
        query=ListToolsByTagsQuery(profession_slug=profession.slug, category_slug=category.slug),
    )
    assert admin_result.curated_apps == [app]
