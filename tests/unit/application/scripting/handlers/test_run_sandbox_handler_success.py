"""Success-path tests for RunSandboxHandler."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionResult,
    RunSandboxCommand,
)
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_snapshot_payload,
    make_tool_run,
    make_tool_session,
    make_tool_version,
    make_ui_payload_with_next_actions,
)

pytest_plugins = [
    "tests.unit.application.scripting.handlers.run_sandbox_fixtures",
    "tests.unit.application.scripting.handlers.sandbox_handler_fixtures",
]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_with_next_actions_returns_state_rev(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    """Run with next_actions → state_rev is returned (not None)."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()
    snapshot_id = uuid4()
    run_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    versions.list_for_tool.return_value = []

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        ui_payload=make_ui_payload_with_next_actions(),
    )
    execute.handle.return_value = ExecuteToolVersionResult(
        run=run, normalized_state={"step": "one"}
    )

    id_generator.new_uuid.side_effect = [snapshot_id, session_id]
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"step": "one"},
        state_rev=1,
    )

    handler = RunSandboxHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        sessions=sessions,
        id_generator=id_generator,
        execute=execute,
        session_files=session_files,
        snapshots=snapshots,
        settings=settings,
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=make_snapshot_payload(),
            input_files=[("input.txt", b"test")],
        ),
    )

    assert result.state_rev == 1
    assert result.run.id == run_id
    sessions.get_or_create.assert_awaited_once()
    sessions.update_state.assert_awaited_once()
    session_files.store_files.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_without_next_actions_returns_none_state_rev(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    """Run without next_actions → state_rev is None, no session persistence."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    id_generator.new_uuid.return_value = snapshot_id
    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    versions.list_for_tool.return_value = []

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        ui_payload=None,
    )
    execute.handle.return_value = ExecuteToolVersionResult(run=run, normalized_state={})

    handler = RunSandboxHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        sessions=sessions,
        id_generator=id_generator,
        execute=execute,
        session_files=session_files,
        snapshots=snapshots,
        settings=settings,
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=make_snapshot_payload(),
            input_files=[("input.txt", b"test")],
        ),
    )

    assert result.state_rev is None
    sessions.get_or_create.assert_not_called()
    sessions.update_state.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_with_empty_next_actions_returns_none_state_rev(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    """Run with ui_payload but empty next_actions → state_rev is None."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    id_generator.new_uuid.return_value = snapshot_id
    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    versions.list_for_tool.return_value = []

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        ui_payload=UiPayloadV2(next_actions=[]),
    )
    execute.handle.return_value = ExecuteToolVersionResult(run=run, normalized_state={})

    handler = RunSandboxHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        sessions=sessions,
        id_generator=id_generator,
        execute=execute,
        session_files=session_files,
        snapshots=snapshots,
        settings=settings,
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=make_snapshot_payload(),
            input_files=[("input.txt", b"test")],
        ),
    )

    assert result.state_rev is None
    sessions.get_or_create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_uses_expected_state_rev_from_session(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    """Verify update_state uses expected_state_rev from get_or_create result."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()
    snapshot_id = uuid4()
    run_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    versions.list_for_tool.return_value = []

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        ui_payload=make_ui_payload_with_next_actions(),
    )
    execute.handle.return_value = ExecuteToolVersionResult(
        run=run, normalized_state={"new": "state"}
    )

    id_generator.new_uuid.side_effect = [snapshot_id, session_id]
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"old": "state"},
        state_rev=5,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"new": "state"},
        state_rev=6,
    )

    handler = RunSandboxHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        sessions=sessions,
        id_generator=id_generator,
        execute=execute,
        session_files=session_files,
        snapshots=snapshots,
        settings=settings,
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=make_snapshot_payload(),
            input_files=[("input.txt", b"test")],
        ),
    )

    assert result.state_rev == 6
    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["expected_state_rev"] == 5
