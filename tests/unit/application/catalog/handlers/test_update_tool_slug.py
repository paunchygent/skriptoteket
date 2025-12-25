from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.commands import UpdateToolSlugCommand
from skriptoteket.application.catalog.handlers.update_tool_slug import UpdateToolSlugHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_slug_requires_admin(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    handler = UpdateToolSlugHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.USER)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolSlugCommand(tool_id=uuid4(), slug="demo-tool"),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    tools_repo.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_slug_rejects_missing_tool(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    tools_repo.get_by_id.return_value = None
    handler = UpdateToolSlugHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolSlugCommand(tool_id=tool_id, slug="demo-tool"),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    tools_repo.update_slug.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_slug_rejects_published_tool(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": True})
    tools_repo.get_by_id.return_value = tool

    handler = UpdateToolSlugHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolSlugCommand(tool_id=tool.id, slug="new-slug"),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    tools_repo.get_by_slug.assert_not_called()
    tools_repo.update_slug.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_slug_rejects_duplicate_slug(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": False, "slug": "old-slug"})
    tools_repo.get_by_id.return_value = tool

    other_tool = make_tool(now=now).model_copy(update={"slug": "new-slug"})
    tools_repo.get_by_slug.return_value = other_tool

    handler = UpdateToolSlugHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolSlugCommand(tool_id=tool.id, slug="new-slug"),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    tools_repo.update_slug.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_slug_normalizes_and_persists(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": False, "slug": "old-slug"})
    tools_repo.get_by_id.return_value = tool
    tools_repo.get_by_slug.return_value = None

    updated = tool.model_copy(update={"slug": "demo-tool", "updated_at": now})
    tools_repo.update_slug.return_value = updated

    handler = UpdateToolSlugHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    result = await handler.handle(
        actor=actor,
        command=UpdateToolSlugCommand(tool_id=tool.id, slug="  Demo-Tool  "),
    )

    assert result.tool.slug == "demo-tool"
    tools_repo.update_slug.assert_awaited_once()
    call = tools_repo.update_slug.await_args.kwargs
    assert call["tool_id"] == tool.id
    assert call["slug"] == "demo-tool"
    assert call["now"] == now
