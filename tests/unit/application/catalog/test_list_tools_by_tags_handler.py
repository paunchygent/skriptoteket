from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.catalog.handlers.list_tools_by_tags import ListToolsByTagsHandler
from skriptoteket.application.catalog.queries import ListToolsByTagsQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from tests.fixtures.catalog_fixtures import make_category, make_profession, make_tool


@pytest.mark.asyncio
async def test_list_tools_by_tags_returns_tools(now: datetime) -> None:
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

    handler = ListToolsByTagsHandler(professions=professions, categories=categories, tools=tools)
    result = await handler.handle(
        ListToolsByTagsQuery(profession_slug=profession.slug, category_slug=category.slug)
    )

    assert result.profession == profession
    assert result.category == category
    assert result.tools == tools_list
    tools.list_by_tags.assert_awaited_once_with(
        profession_id=profession.id,
        category_id=category.id,
    )


@pytest.mark.asyncio
async def test_list_tools_by_tags_raises_when_profession_missing() -> None:
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = None

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)

    handler = ListToolsByTagsHandler(professions=professions, categories=categories, tools=tools)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ListToolsByTagsQuery(profession_slug="nope", category_slug="x"))

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    categories.get_for_profession_by_slug.assert_not_awaited()
    tools.list_by_tags.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_tools_by_tags_raises_when_category_not_in_profession(now: datetime) -> None:
    profession = make_profession(now=now)

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = profession

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.get_for_profession_by_slug.return_value = None

    tools = AsyncMock(spec=ToolRepositoryProtocol)

    handler = ListToolsByTagsHandler(professions=professions, categories=categories, tools=tools)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            ListToolsByTagsQuery(profession_slug=profession.slug, category_slug="nope")
        )

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    tools.list_by_tags.assert_not_awaited()
