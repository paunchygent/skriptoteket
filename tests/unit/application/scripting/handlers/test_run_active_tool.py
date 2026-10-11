from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    RunActiveToolCommand,
)
from skriptoteket.application.scripting.handlers.run_active_tool import (
    RunActiveToolHandler,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import RunContext, VersionState
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction, UiPayloadV2
from skriptoteket.domain.scripting.ui.state_update import SetStateUpdate
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileContent, SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.run_active_tool_test_support import (
    FakeUow,
    make_tool_run,
    make_tool_version,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_success_returns_tool_run(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    version = make_tool_version(
        tool_id=tool.id,
        version_id=active_version_id,
        version_number=1,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=actor.id,
        context=RunContext.PRODUCTION,
        now=now,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    execute.handle.return_value = ExecuteToolVersionResult(run=run)
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

    result = await handler.handle(
        actor=actor,
        command=RunActiveToolCommand(
            tool_slug=tool.slug,
            input_files_by_field={"documents": [("test.xlsx", b"test data")]},
        ),
    )

    assert result.run.id == run.id
    assert result.run.context is RunContext.PRODUCTION

    # Verify execute was called with PRODUCTION context
    execute.handle.assert_awaited_once()
    call_args = execute.handle.call_args
    assert call_args.kwargs["actor"] == actor
    cmd = call_args.kwargs["command"]
    assert isinstance(cmd, ExecuteToolVersionCommand)
    assert cmd.tool_id == tool.id
    assert cmd.version_id == version.id
    assert cmd.context is RunContext.PRODUCTION
    assert cmd.session_context == "default"
    assert cmd.input_files_by_field == {"documents": [("test.xlsx", b"test data")]}
    session_files.upsert_files.assert_awaited_once()
    upsert_kwargs = session_files.upsert_files.call_args.kwargs
    assert upsert_kwargs["files"] == [
        SessionFileContent(name="test.xlsx", content=b"test data", field="documents")
    ]

    assert uow.entered is True
    assert uow.exited is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_active_tool_persists_session_state_when_run_has_next_actions(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER)
    active_version_id = uuid4()
    tool = make_tool(now=now, is_published=True).model_copy(
        update={"active_version_id": active_version_id}
    )

    version = make_tool_version(
        tool_id=tool.id,
        version_id=active_version_id,
        version_number=1,
        state=VersionState.ACTIVE,
        created_by_user_id=uuid4(),
        now=now,
    )

    run = make_tool_run(
        run_id=uuid4(),
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=actor.id,
        context=RunContext.PRODUCTION,
        now=now,
        ui_payload=UiPayloadV2(next_actions=[UiFormAction(action_id="next", label="Next")]),
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_slug.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    execute.handle.return_value = ExecuteToolVersionResult(
        run=run,
        state_update=SetStateUpdate(state={"step": "one"}),
    )

    session_id = uuid4()
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    sessions.get_or_create.return_value = ToolSession(
        id=session_id,
        tool_id=tool.id,
        user_id=actor.id,
        context="default",
        state={},
        state_rev=0,
        created_at=now,
        updated_at=now,
    )
    sessions.update_state.return_value = ToolSession(
        id=session_id,
        tool_id=tool.id,
        user_id=actor.id,
        context="default",
        state={"step": "one"},
        state_rev=1,
        created_at=now,
        updated_at=now,
    )

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id
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

    await handler.handle(
        actor=actor,
        command=RunActiveToolCommand(
            tool_slug=tool.slug,
            input_files_by_field={"documents": [("input.txt", b"test")]},
        ),
    )

    sessions.update_state.assert_awaited_once()
    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["tool_id"] == tool.id
    assert update_kwargs["user_id"] == actor.id
    assert update_kwargs["context"] == "default"
    assert update_kwargs["expected_state_rev"] == 0
    assert update_kwargs["state"] == {"step": "one"}
