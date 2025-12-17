from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.handlers.list_maintainers import ListMaintainersHandler
from skriptoteket.application.catalog.queries import ListMaintainersQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_maintainers_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(now=now)

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)

    handler = ListMaintainersHandler(tools=tools, maintainers=maintainers, users=users)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListMaintainersQuery(tool_id=tool.id))

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    tools.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_maintainers_rejects_missing_tool(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)

    handler = ListMaintainersHandler(tools=tools, maintainers=maintainers, users=users)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListMaintainersQuery(tool_id=tool_id))

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    maintainers.list_maintainers.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_maintainers_returns_empty_list_when_no_maintainers(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.list_maintainers.return_value = []

    users = AsyncMock(spec=UserRepositoryProtocol)

    handler = ListMaintainersHandler(tools=tools, maintainers=maintainers, users=users)

    result = await handler.handle(actor=actor, query=ListMaintainersQuery(tool_id=tool.id))

    assert result.tool_id == tool.id
    assert result.maintainers == []
    maintainers.list_maintainers.assert_awaited_once_with(tool_id=tool.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_maintainers_returns_user_objects_for_maintainers(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    maintainer1 = make_user(role=Role.CONTRIBUTOR, email="m1@example.com")
    maintainer2 = make_user(role=Role.CONTRIBUTOR, email="m2@example.com")

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.list_maintainers.return_value = [maintainer1.id, maintainer2.id]

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.side_effect = lambda *, user_id: (
        maintainer1 if user_id == maintainer1.id else maintainer2
    )

    handler = ListMaintainersHandler(tools=tools, maintainers=maintainers, users=users)

    result = await handler.handle(actor=actor, query=ListMaintainersQuery(tool_id=tool.id))

    assert result.tool_id == tool.id
    assert len(result.maintainers) == 2
    assert maintainer1 in result.maintainers
    assert maintainer2 in result.maintainers
