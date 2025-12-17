from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.handlers.list_tools_for_contributor import (
    ListToolsForContributorHandler,
)
from skriptoteket.application.catalog.queries import ListToolsForContributorQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_for_contributor_requires_contributor(now: datetime) -> None:
    actor = make_user(role=Role.USER)

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)

    handler = ListToolsForContributorHandler(tools=tools, maintainers=maintainers)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListToolsForContributorQuery())

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    maintainers.list_tools_for_user.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_for_contributor_returns_empty_list_when_no_tools(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.list_tools_for_user.return_value = []

    handler = ListToolsForContributorHandler(tools=tools, maintainers=maintainers)

    result = await handler.handle(actor=actor, query=ListToolsForContributorQuery())

    assert result.tools == []
    maintainers.list_tools_for_user.assert_awaited_once_with(user_id=actor.id)
    tools.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_for_contributor_returns_tools_for_maintainer(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())
    tool1 = make_tool(now=now, slug="tool-1", title="Tool 1")
    tool2 = make_tool(now=now, slug="tool-2", title="Tool 2")

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.side_effect = lambda *, tool_id: tool1 if tool_id == tool1.id else tool2

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.list_tools_for_user.return_value = [tool1.id, tool2.id]

    handler = ListToolsForContributorHandler(tools=tools, maintainers=maintainers)

    result = await handler.handle(actor=actor, query=ListToolsForContributorQuery())

    assert len(result.tools) == 2
    assert tool1 in result.tools
    assert tool2 in result.tools
    maintainers.list_tools_for_user.assert_awaited_once_with(user_id=actor.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_for_contributor_filters_deleted_tools(now: datetime) -> None:
    """If a tool was deleted but maintainer relation remains, it should not appear in results."""
    actor = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())
    tool1 = make_tool(now=now, slug="tool-1", title="Tool 1")
    deleted_tool_id = uuid4()

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.side_effect = lambda *, tool_id: tool1 if tool_id == tool1.id else None

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.list_tools_for_user.return_value = [tool1.id, deleted_tool_id]

    handler = ListToolsForContributorHandler(tools=tools, maintainers=maintainers)

    result = await handler.handle(actor=actor, query=ListToolsForContributorQuery())

    assert len(result.tools) == 1
    assert tool1 in result.tools
