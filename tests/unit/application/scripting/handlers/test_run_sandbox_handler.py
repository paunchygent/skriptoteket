"""Tests for RunSandboxHandler (ADR-0038 state persistence)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionResult,
    RunSandboxCommand,
)
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
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
    make_ui_payload_with_next_actions,
)

# -----------------------------------------------------------------------------
# State Persistence Tests (ADR-0038 core feature)
# -----------------------------------------------------------------------------


@pytest.fixture
def session_files() -> AsyncMock:
    return AsyncMock(spec=SessionFileStorageProtocol)


@pytest.fixture
def locks() -> AsyncMock:
    return AsyncMock(spec=DraftLockRepositoryProtocol)


@pytest.fixture
def clock(now: datetime) -> Mock:
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    return clock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_with_next_actions_returns_state_rev(
    now: datetime, session_files: AsyncMock, locks: AsyncMock, clock: Mock
) -> None:
    """Run with next_actions → state_rev is returned (not None)."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()
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

    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
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
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
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
) -> None:
    """Run without next_actions → state_rev is None, no session persistence."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
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
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
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
) -> None:
    """Run with ui_payload but empty next_actions → state_rev is None."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
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
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            input_files=[("input.txt", b"test")],
        ),
    )

    assert result.state_rev is None
    sessions.get_or_create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_persists_session_with_correct_context(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    """Verify session uses sandbox:<version_id> context format."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()
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
        run=run, normalized_state={"data": "value"}
    )

    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state={"data": "value"},
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
    )

    await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            input_files=[("input.txt", b"test")],
        ),
    )

    get_or_create_kwargs = sessions.get_or_create.call_args.kwargs
    assert get_or_create_kwargs["context"] == f"sandbox:{version_id}"

    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["context"] == f"sandbox:{version_id}"
    assert update_kwargs["state"] == {"data": "value"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_uses_expected_state_rev_from_session(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    """Verify update_state uses expected_state_rev from get_or_create result."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()
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

    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
        now=now,
        state={"old": "state"},
        state_rev=5,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox:{version_id}",
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
    )

    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            input_files=[("input.txt", b"test")],
        ),
    )

    assert result.state_rev == 6
    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["expected_state_rev"] == 5


# -----------------------------------------------------------------------------
# Error Condition Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_when_version_not_found_raises_not_found(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    """versions.get_by_id() returns None → NOT_FOUND."""
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = None

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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[("input.txt", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_when_version_tool_id_mismatch_raises_conflict(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
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
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=different_tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    versions.list_for_tool.return_value = []

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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[("input.txt", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    execute.handle.assert_not_called()


# -----------------------------------------------------------------------------
# Permission Tests
# -----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_contributor_not_maintainer_raises_forbidden(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    """CONTRIBUTOR + is_maintainer=False → FORBIDDEN."""
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    version_id = uuid4()

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
    maintainers.is_maintainer.return_value = False

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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[("input.txt", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_user_role_raises_insufficient_permissions(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    """USER role → FORBIDDEN before any work."""
    actor = make_user(role=Role.USER)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[("input.txt", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    versions.get_by_id.assert_not_called()


# -----------------------------------------------------------------------------
# Draft Lock Enforcement Tests (ST-14-07)
# -----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_requires_active_draft_lock(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[],
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_rejects_lock_owned_by_another_user(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    other_user_id = uuid4()
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[],
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_rejects_non_head_draft_version(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    head_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
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
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                input_files=[],
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    locks.get_for_tool.assert_not_called()
    execute.handle.assert_not_called()
