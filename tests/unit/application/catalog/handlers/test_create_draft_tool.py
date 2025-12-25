from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.commands import CreateDraftToolCommand
from skriptoteket.application.catalog.handlers.create_draft_tool import CreateDraftToolHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import (
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
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
async def test_create_draft_tool_requires_admin(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers_repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = CreateDraftToolHandler(
        uow=uow,
        tools=tools_repo,
        maintainers=maintainers_repo,
        clock=clock,
        id_generator=id_generator,
    )

    actor = make_user(role=Role.USER)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=CreateDraftToolCommand(title="My tool", summary=None),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    tools_repo.create_draft.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_tool_creates_tool_and_adds_maintainer(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers_repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)

    tool_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=tool_id))
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    actor = make_user(role=Role.ADMIN)
    persisted_tool = make_tool(
        now=now,
        tool_id=tool_id,
        owner_user_id=actor.id,
        slug=f"draft-{tool_id}",
        title="My tool",
        summary=None,
    )
    tools_repo.create_draft.return_value = persisted_tool

    handler = CreateDraftToolHandler(
        uow=uow,
        tools=tools_repo,
        maintainers=maintainers_repo,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=CreateDraftToolCommand(title="  My tool  ", summary="  "),
    )

    assert result.tool.id == tool_id
    assert uow.entered is True
    assert uow.exited is True

    tools_repo.create_draft.assert_awaited_once()
    created_tool = tools_repo.create_draft.await_args.kwargs["tool"]
    assert created_tool.id == tool_id
    assert created_tool.owner_user_id == actor.id
    assert created_tool.slug == f"draft-{tool_id}"
    assert created_tool.title == "My tool"
    assert created_tool.summary is None

    assert tools_repo.create_draft.await_args.kwargs["profession_ids"] == []
    assert tools_repo.create_draft.await_args.kwargs["category_ids"] == []

    maintainers_repo.add_maintainer.assert_awaited_once_with(tool_id=tool_id, user_id=actor.id)
