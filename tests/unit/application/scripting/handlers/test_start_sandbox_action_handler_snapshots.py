"""Snapshot-specific tests for StartSandboxActionHandler."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import ExecuteToolVersionResult
from skriptoteket.application.scripting.handlers.start_sandbox_action import (
    StartSandboxActionHandler,
)
from skriptoteket.application.scripting.interactive_sandbox import (
    StartSandboxActionCommand,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
from skriptoteket.domain.scripting.tool_settings import (
    ToolSettingsSchema,
    compute_sandbox_settings_context,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiStringField
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
async def test_start_sandbox_action_uses_sandbox_context_format(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """Verify context is sandbox:<snapshot_id> (ADR-0044)."""
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
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state_rev=1,
    )

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
    )
    execute.handle.return_value = ExecuteToolVersionResult(run=run, normalized_state={})

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
        actor=actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_id=snapshot_id,
            action_id="next_step",
            input={},
            expected_state_rev=0,
        ),
    )

    call_kwargs = sessions.get.call_args.kwargs
    assert call_kwargs["context"] == f"sandbox:{snapshot_id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_passes_settings_context_override(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()
    run_id = uuid4()

    schema: ToolSettingsSchema = [UiStringField(name="theme_color", label="Färgtema")]

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    versions.list_for_tool.return_value = []
    snapshots.get_by_id.return_value = SandboxSnapshot(
        id=snapshot_id,
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=actor.id,
        entrypoint="run_tool",
        source_code="print('ok')",
        settings_schema=schema,
        input_schema=None,
        usage_instructions=None,
        payload_bytes=100,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state_rev=1,
    )

    run = make_tool_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
    )
    execute.handle.return_value = ExecuteToolVersionResult(run=run, normalized_state={})

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
        actor=actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_id=snapshot_id,
            action_id="next_step",
            input={},
            expected_state_rev=0,
        ),
    )

    execute_kwargs = execute.handle.call_args.kwargs
    execute_command = execute_kwargs["command"]
    assert execute_command.settings_context == compute_sandbox_settings_context(
        draft_head_id=version_id,
        settings_schema=schema,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_snapshot_not_found_raises_not_found(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
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
    snapshots.get_by_id.return_value = None

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

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
                snapshot_id=snapshot_id,
                action_id="next_step",
                input={},
                expected_state_rev=0,
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    sessions.get.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_snapshot_expired_raises_conflict(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
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
        expired=True,
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

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
                snapshot_id=snapshot_id,
                action_id="next_step",
                input={},
                expected_state_rev=0,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    sessions.get.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_snapshot_tool_id_mismatch_raises_conflict(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    other_tool_id = uuid4()
    version_id = uuid4()
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
        tool_id=other_tool_id,
        draft_head_id=version_id,
        created_by_user_id=actor.id,
        now=now,
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

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
                snapshot_id=snapshot_id,
                action_id="next_step",
                input={},
                expected_state_rev=0,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    sessions.get.assert_not_called()
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_snapshot_draft_head_mismatch_raises_conflict(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    other_version_id = uuid4()
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
        draft_head_id=other_version_id,
        created_by_user_id=actor.id,
        now=now,
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

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
                snapshot_id=snapshot_id,
                action_id="next_step",
                input={},
                expected_state_rev=0,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    sessions.get.assert_not_called()
    execute.handle.assert_not_called()
