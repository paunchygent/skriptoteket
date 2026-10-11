from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import RunActiveToolCommand
from skriptoteket.application.scripting.handlers.run_active_tool import (
    RunActiveToolHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.run_active_tool_test_support import (
    FakeUow,
    make_tool_version,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_tool_missing(now: datetime) -> None:
    actor = make_user(role=Role.USER)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = None
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug="nonexistent-tool",
                input_files_by_field={"documents": [("test.xlsx", b"test")]},
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_tool_not_published(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=False)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files_by_field={"documents": [("test.xlsx", b"test")]},
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_no_active_version_id(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    tool = make_tool(now=now, is_published=True)
    # Tool is published but has no active_version_id (default is None)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files_by_field={"documents": [("test.xlsx", b"test")]},
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_version_missing(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = None
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files_by_field={"documents": [("test.xlsx", b"test")]},
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    versions.get_by_id.assert_awaited_once_with(version_id=active_version_id)
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_raises_not_found_when_version_not_active(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    # Version exists but is not in ACTIVE state (data drift)
    version = make_tool_version(
        tool_id=tool.id,
        version_id=active_version_id,
        version_number=1,
        state=VersionState.DRAFT,  # Wrong state!
        created_by_user_id=uuid4(),
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    handler = RunActiveToolHandler(
        uow=uow,
        tools=tools,
        versions=versions,
        execute=execute,
        sessions=sessions,
        id_generator=id_generator,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunActiveToolCommand(
                tool_slug=tool.slug,
                input_files_by_field={"documents": [("test.xlsx", b"test")]},
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    execute.handle.assert_not_called()
