"""Success-path tests for StartSandboxActionHandler."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
)
from skriptoteket.application.scripting.handlers.start_sandbox_action import (
    StartSandboxActionHandler,
)
from skriptoteket.application.scripting.interactive_sandbox import (
    StartSandboxActionCommand,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_sandbox_snapshot,
    make_tool_run,
    make_tool_session,
    make_tool_version,
)

pytest_plugins = [
    "tests.unit.application.scripting.handlers.sandbox_handler_fixtures",
]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_success_returns_run_id_and_state_rev(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """Full success flow: session exists, state_rev matches, execute, update state."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    versions.list_for_tool.return_value = []
    snapshots.get_by_id.return_value = make_sandbox_snapshot(
        snapshot_id=snapshot_id,
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=actor.id,
        now=now,
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"step": "one"},
        state_rev=1,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"step": "two"},
        state_rev=2,
    )

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
    )
    execute.handle.return_value = ExecuteToolVersionResult(
        run=run, normalized_state={"step": "two"}
    )

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
        snapshots=snapshots,
    )

    result = await handler.handle(
        actor=actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_id=snapshot_id,
            action_id="next_step",
            input={"confirm": True},
            expected_state_rev=1,
        ),
    )

    assert result.run_id == run_id
    assert result.state_rev == 2
    execute.handle.assert_awaited_once()
    assert uow.enter_count == 2  # validation + state update


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_builds_correct_payload_structure(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """Verify action.json payload has {action_id, input, state}."""
    outer_actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=outer_actor.id,
    )
    versions.list_for_tool.return_value = []
    snapshots.get_by_id.return_value = make_sandbox_snapshot(
        snapshot_id=snapshot_id,
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=outer_actor.id,
        now=now,
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=outer_actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"existing": "state"},
        state_rev=5,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=outer_actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state={"new": "state"},
        state_rev=6,
    )

    captured_command: ExecuteToolVersionCommand | None = None

    async def _capture_execute(
        *,
        actor: object,
        command: ExecuteToolVersionCommand,
    ) -> ExecuteToolVersionResult:
        del actor
        nonlocal captured_command
        captured_command = command
        run = make_tool_run(
            run_id=run_id,
            tool_id=tool_id,
            version_id=version_id,
            requested_by_user_id=outer_actor.id,
            now=now,
        )
        return ExecuteToolVersionResult(run=run, normalized_state={"new": "state"})

    execute.handle.side_effect = _capture_execute

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
        snapshots=snapshots,
    )

    await handler.handle(
        actor=outer_actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_id=snapshot_id,
            action_id="confirm_action",
            input={"user_choice": "yes"},
            expected_state_rev=5,
        ),
    )

    assert captured_command is not None
    # action.json (no persisted files in this test)
    filename, content = captured_command.input_files[0]
    assert filename == "action.json"
    payload = json.loads(content.decode("utf-8"))
    assert payload["action_id"] == "confirm_action"
    assert payload["input"] == {"user_choice": "yes"}
    assert payload["state"] == {"existing": "state"}
