from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.handlers.list_tool_taxonomy import (
    ListToolTaxonomyHandler,
)
from skriptoteket.application.catalog.queries import ListToolTaxonomyQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tool_taxonomy_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(now=now)

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    handler = ListToolTaxonomyHandler(tools=tools)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListToolTaxonomyQuery(tool_id=tool.id))

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    tools.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tool_taxonomy_rejects_missing_tool(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    handler = ListToolTaxonomyHandler(tools=tools)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListToolTaxonomyQuery(tool_id=tool_id))

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    tools.list_tag_ids.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tool_taxonomy_returns_ids(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    profession_ids = [uuid4(), uuid4()]
    category_ids = [uuid4()]

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    tools.list_tag_ids.return_value = (profession_ids, category_ids)

    handler = ListToolTaxonomyHandler(tools=tools)

    result = await handler.handle(actor=actor, query=ListToolTaxonomyQuery(tool_id=tool.id))

    assert result.tool_id == tool.id
    assert result.profession_ids == profession_ids
    assert result.category_ids == category_ids
    tools.list_tag_ids.assert_awaited_once_with(tool_id=tool.id)
