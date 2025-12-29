"""Error-path tests for StartSandboxActionHandler."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.handlers.start_sandbox_action import (
    StartSandboxActionHandler,
)
from skriptoteket.application.scripting.interactive_sandbox import (
    StartSandboxActionCommand,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
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
    make_tool_session,
    make_tool_version,
)

pytest_plugins = [
    "tests.unit.application.scripting.handlers.sandbox_handler_fixtures",
]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_when_session_missing_raises_not_found(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """sessions.get() returns None → NOT_FOUND."""
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
    )
    sessions.get.return_value = None

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
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_when_state_rev_mismatch_raises_conflict(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """expected_state_rev mismatch → CONFLICT, execute not called."""
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
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{snapshot_id}",
        now=now,
        state_rev=3,
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
                expected_state_rev=1,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.details["expected_state_rev"] == 1
    assert exc_info.value.details["current_state_rev"] == 3
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_when_version_not_found_raises_not_found(
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """versions.get_by_id() returns None → NOT_FOUND."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = None

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
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_when_version_tool_id_mismatch_raises_conflict(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """version.tool_id != command.tool_id → CONFLICT."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    different_tool_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=different_tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    versions.list_for_tool.return_value = []

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
    execute.handle.assert_not_called()
