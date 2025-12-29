"""Permission and lock enforcement tests for StartSandboxActionHandler."""

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
from skriptoteket.domain.scripting.draft_locks import DraftLock
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
async def test_start_sandbox_action_contributor_not_maintainer_raises_forbidden(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """CONTRIBUTOR + is_maintainer=False → FORBIDDEN."""
    actor = make_user(role=Role.CONTRIBUTOR)
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
    maintainers.is_maintainer.return_value = False

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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_contributor_other_user_draft_raises_forbidden(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """CONTRIBUTOR + own draft=False → FORBIDDEN."""
    actor = make_user(role=Role.CONTRIBUTOR)
    other_user_id = uuid4()
    tool_id = uuid4()
    version_id = uuid4()
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
        created_by_user_id=other_user_id,
    )
    versions.list_for_tool.return_value = []
    maintainers.is_maintainer.return_value = True

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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_admin_bypasses_maintainer_check(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """ADMIN can run any sandbox action without maintainer check."""
    actor = make_user(role=Role.ADMIN)
    other_user_id = uuid4()
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
        created_by_user_id=other_user_id,
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

    result = await handler.handle(
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

    assert result.run_id == run_id
    maintainers.is_maintainer.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_user_role_raises_insufficient_permissions(
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    """USER role → raised before any work."""
    actor = make_user(role=Role.USER)
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    versions.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_requires_active_draft_lock(
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

    draft = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    versions.get_by_id.return_value = draft
    versions.list_for_tool.return_value = [draft]
    locks.get_for_tool.return_value = None

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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_rejects_lock_owned_by_another_user(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    other_user_id = uuid4()
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    draft = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    versions.get_by_id.return_value = draft
    versions.list_for_tool.return_value = [draft]
    locks.get_for_tool.return_value = DraftLock(
        tool_id=tool_id,
        draft_head_id=version_id,
        locked_by_user_id=other_user_id,
        locked_at=now,
        expires_at=now + timedelta(minutes=5),
        forced_by_user_id=None,
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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_rejects_non_head_draft_version(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    head_id = uuid4()
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
        created_by_user_id=actor.id,
    )
    versions.list_for_tool.return_value = [
        make_tool_version(
            version_id=head_id,
            tool_id=tool_id,
            now=now,
            created_by_user_id=actor.id,
            version_number=2,
        )
    ]

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
    locks.get_for_tool.assert_not_called()
    execute.handle.assert_not_called()
