"""Tests for StartSandboxActionHandler (ADR-0038)."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock
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
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_tool_run,
    make_tool_session,
    make_tool_version,
)

# -----------------------------------------------------------------------------
# Priority 1: Core Flow Tests
# -----------------------------------------------------------------------------


@pytest.fixture
def session_files() -> AsyncMock:
    storage = AsyncMock(spec=SessionFileStorageProtocol)
    storage.get_files.return_value = []
    return storage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_success_returns_run_id_and_state_rev(
    now: datetime,
    session_files: AsyncMock,
) -> None:
    """Full success flow: session exists, state_rev matches, execute, update state."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state={"step": "one"},
        state_rev=1,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
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
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    result = await handler.handle(
        actor=actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
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
) -> None:
    """Verify action.json payload has {action_id, input, state}."""
    outer_actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

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
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=outer_actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state={"existing": "state"},
        state_rev=5,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=outer_actor.id,
        context=f"sandbox:{version_id}",
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
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    await handler.handle(
        actor=outer_actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
            action_id="confirm_action",
            input={"user_choice": "yes"},
            expected_state_rev=5,
        ),
    )

    assert captured_command is not None
    filename, content = captured_command.input_files[0]
    assert filename == "action.json"
    payload = json.loads(content.decode("utf-8"))
    assert payload["action_id"] == "confirm_action"
    assert payload["input"] == {"user_choice": "yes"}
    assert payload["state"] == {"existing": "state"}


# -----------------------------------------------------------------------------
# Priority 2: Error Condition Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_when_session_missing_raises_not_found(
    now: datetime,
    session_files: AsyncMock,
) -> None:
    """sessions.get() returns None → NOT_FOUND."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    sessions.get.return_value = None

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
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
) -> None:
    """expected_state_rev mismatch → CONFLICT, execute not called."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state_rev=3,
    )

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
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
    now: datetime,
    session_files: AsyncMock,
) -> None:
    """versions.get_by_id() returns None → NOT_FOUND."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

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
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
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
) -> None:
    """version.tool_id != command.tool_id → CONFLICT."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    different_tool_id = uuid4()

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

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
                action_id="next_step",
                input={},
                expected_state_rev=0,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    execute.handle.assert_not_called()


# -----------------------------------------------------------------------------
# Priority 3: Permission Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_contributor_not_maintainer_raises_forbidden(
    now: datetime,
    session_files: AsyncMock,
) -> None:
    """CONTRIBUTOR + is_maintainer=False → FORBIDDEN."""
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    maintainers.is_maintainer.return_value = False

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
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
) -> None:
    """CONTRIBUTOR + own draft=False → FORBIDDEN."""
    actor = make_user(role=Role.CONTRIBUTOR)
    other_user_id = uuid4()
    tool_id = uuid4()
    version_id = uuid4()

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
    maintainers.is_maintainer.return_value = True

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
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
) -> None:
    """ADMIN can run any sandbox action without maintainer check."""
    actor = make_user(role=Role.ADMIN)
    other_user_id = uuid4()
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

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
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
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
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    result = await handler.handle(
        actor=actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
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
    now: datetime,
    session_files: AsyncMock,
) -> None:
    """USER role → raised before any work."""
    actor = make_user(role=Role.USER)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    handler = StartSandboxActionHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=StartSandboxActionCommand(
                tool_id=tool_id,
                version_id=version_id,
                action_id="next_step",
                input={},
                expected_state_rev=0,
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    versions.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_uses_sandbox_context_format(
    now: datetime,
    session_files: AsyncMock,
) -> None:
    """Verify context is sandbox:<version_id>."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    run_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id, tool_id=tool_id, now=now, created_by_user_id=actor.id
    )
    sessions.get.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
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
        sessions=sessions,
        execute=execute,
        session_files=session_files,
    )

    await handler.handle(
        actor=actor,
        command=StartSandboxActionCommand(
            tool_id=tool_id,
            version_id=version_id,
            action_id="next_step",
            input={},
            expected_state_rev=0,
        ),
    )

    call_kwargs = sessions.get.call_args.kwargs
    assert call_kwargs["context"] == f"sandbox:{version_id}"
