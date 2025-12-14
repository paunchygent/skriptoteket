from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.catalog.commands import DepublishToolCommand, PublishToolCommand
from skriptoteket.application.catalog.handlers.depublish_tool import DepublishToolHandler
from skriptoteket.application.catalog.handlers.list_tools_for_admin import ListToolsForAdminHandler
from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.queries import ListToolsForAdminQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import ToolVersion, VersionState, compute_content_hash
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
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


def make_tool_version(*, tool_id: UUID, now: datetime, state: VersionState) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    return ToolVersion(
        id=uuid4(),
        tool_id=tool_id,
        version_number=1,
        state=state,
        source_code=source_code,
        entrypoint="run_tool",
        content_hash=compute_content_hash(entrypoint="run_tool", source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=uuid4(),
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_for_admin_requires_admin(now: datetime) -> None:
    del now
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    handler = ListToolsForAdminHandler(tools=tools_repo)

    actor = make_user(role=Role.CONTRIBUTOR)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListToolsForAdminQuery())

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    tools_repo.list_all.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tools_for_admin_returns_tools(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    tools_repo.list_all.return_value = [make_tool(now=now)]
    handler = ListToolsForAdminHandler(tools=tools_repo)

    result = await handler.handle(actor=actor, query=ListToolsForAdminQuery())

    assert len(result.tools) == 1
    tools_repo.list_all.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_requires_admin(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.USER)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=PublishToolCommand(tool_id=uuid4()))

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    tools_repo.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_rejects_missing_tool(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tools_repo.get_by_id.return_value = None

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool_id))

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_is_idempotent_when_already_published(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": True})
    tools_repo.get_by_id.return_value = tool

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    result = await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    assert result.tool.is_published is True
    versions_repo.get_by_id.assert_not_called()
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_rejects_missing_active_version(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": False, "active_version_id": None})
    tools_repo.get_by_id.return_value = tool

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    versions_repo.get_by_id.assert_not_called()
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_rejects_missing_active_version_record(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    active_version_id = uuid4()
    tool = make_tool(now=now).model_copy(update={"active_version_id": active_version_id})
    tools_repo.get_by_id.return_value = tool
    versions_repo.get_by_id.return_value = None

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    assert exc_info.value.code is ErrorCode.CONFLICT
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_rejects_active_version_for_other_tool(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    active_version_id = uuid4()
    tool = make_tool(now=now).model_copy(update={"active_version_id": active_version_id})
    tools_repo.get_by_id.return_value = tool

    version = make_tool_version(tool_id=uuid4(), now=now, state=VersionState.ACTIVE).model_copy(
        update={"id": active_version_id}
    )
    versions_repo.get_by_id.return_value = version

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    assert exc_info.value.code is ErrorCode.CONFLICT
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_rejects_non_active_version_state(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    active_version_id = uuid4()
    tool = make_tool(now=now).model_copy(update={"active_version_id": active_version_id})
    tools_repo.get_by_id.return_value = tool

    version = make_tool_version(tool_id=tool.id, now=now, state=VersionState.DRAFT).model_copy(
        update={"id": active_version_id}
    )
    versions_repo.get_by_id.return_value = version

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    assert exc_info.value.code is ErrorCode.CONFLICT
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_tool_persists_state_change(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    active_version_id = uuid4()
    tool = make_tool(now=now).model_copy(update={"active_version_id": active_version_id})
    tools_repo.get_by_id.return_value = tool

    version = make_tool_version(tool_id=tool.id, now=now, state=VersionState.ACTIVE).model_copy(
        update={"id": active_version_id}
    )
    versions_repo.get_by_id.return_value = version

    updated_tool = tool.model_copy(update={"is_published": True, "updated_at": now})
    tools_repo.set_published.return_value = updated_tool

    handler = PublishToolHandler(uow=uow, tools=tools_repo, versions=versions_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    result = await handler.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    assert result.tool.is_published is True
    tools_repo.set_published.assert_awaited_once()
    call = tools_repo.set_published.await_args.kwargs
    assert call["tool_id"] == tool.id
    assert call["is_published"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_depublish_tool_requires_admin(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    handler = DepublishToolHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.USER)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=DepublishToolCommand(tool_id=uuid4()))

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    tools_repo.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_depublish_tool_rejects_missing_tool(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tools_repo.get_by_id.return_value = None

    handler = DepublishToolHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=DepublishToolCommand(tool_id=tool_id))

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_depublish_tool_is_idempotent_when_already_depublished(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": False})
    tools_repo.get_by_id.return_value = tool

    handler = DepublishToolHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    result = await handler.handle(actor=actor, command=DepublishToolCommand(tool_id=tool.id))

    assert result.tool.is_published is False
    tools_repo.set_published.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_depublish_tool_persists_state_change(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    tool = make_tool(now=now).model_copy(update={"is_published": True})
    tools_repo.get_by_id.return_value = tool

    updated_tool = tool.model_copy(update={"is_published": False, "updated_at": now})
    tools_repo.set_published.return_value = updated_tool

    handler = DepublishToolHandler(uow=uow, tools=tools_repo, clock=clock)

    actor = make_user(role=Role.ADMIN)
    result = await handler.handle(actor=actor, command=DepublishToolCommand(tool_id=tool.id))

    assert result.tool.is_published is False
    tools_repo.set_published.assert_awaited_once()
    call = tools_repo.set_published.await_args.kwargs
    assert call["tool_id"] == tool.id
    assert call["is_published"] is False
