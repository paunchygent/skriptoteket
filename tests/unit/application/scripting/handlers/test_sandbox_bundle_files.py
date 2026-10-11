"""Sandbox runs of gruppgenerator's real bundle carry the editor's unsaved bundle edits."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionResult,
    RunSandboxCommand,
    SandboxSnapshotPayload,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.application.scripting.handlers.start_sandbox_action import (
    StartSandboxActionHandler,
)
from skriptoteket.application.scripting.interactive_sandbox import StartSandboxActionCommand
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
from skriptoteket.domain.scripting.ui.state_update import SetStateUpdate
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.gruppgenerator_bundle_support import (
    edited_roster_py,
    gruppgenerator_draft,
    gruppgenerator_files,
)
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_tool_run,
    make_tool_session,
)

pytest_plugins = [
    "tests.unit.application.scripting.handlers.run_sandbox_fixtures",
    "tests.unit.application.scripting.handlers.sandbox_handler_fixtures",
]


def _run_sandbox_handler(
    *,
    actor: User,
    tool_id: UUID,
    version_id: UUID,
    now: datetime,
    execute: AsyncMock,
    snapshot_id: UUID,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> RunSandboxHandler:
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = gruppgenerator_draft(
        version_id=version_id, tool_id=tool_id, created_by_user_id=actor.id, now=now
    )
    versions.list_for_tool.return_value = []
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    session = make_tool_session(
        tool_id=tool_id, user_id=actor.id, context=f"sandbox:{snapshot_id}", now=now
    )
    sessions.get_or_create.return_value = session
    sessions.update_state.return_value = session
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [snapshot_id, uuid4()]
    execute.handle.return_value = ExecuteToolVersionResult(
        run=make_tool_run(
            tool_id=tool_id, version_id=version_id, requested_by_user_id=actor.id, now=now
        ),
        state_update=SetStateUpdate(state={}),
    )
    return RunSandboxHandler(
        uow=FakeUow(),
        versions=versions,
        maintainers=AsyncMock(spec=ToolMaintainerRepositoryProtocol),
        sessions=sessions,
        id_generator=id_generator,
        execute=execute,
        session_files=session_files,
        locks=locks,
        clock=clock,
        snapshots=snapshots,
        settings=settings,
    )


def _snapshot_payload(bundle_files: dict[str, str]) -> SandboxSnapshotPayload:
    source_code, _ = gruppgenerator_files()
    return SandboxSnapshotPayload(
        entrypoint="run_tool", source_code=source_code, bundle_files=bundle_files
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_runs_and_stores_the_unsaved_roster_edit(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id, version_id, snapshot_id = uuid4(), uuid4(), uuid4()
    _, saved_bundle = gruppgenerator_files()
    edited_bundle = {**saved_bundle, "roster.py": edited_roster_py(saved_bundle["roster.py"])}
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    handler = _run_sandbox_handler(
        actor=actor,
        tool_id=tool_id,
        version_id=version_id,
        now=now,
        execute=execute,
        snapshot_id=snapshot_id,
        session_files=session_files,
        locks=locks,
        clock=clock,
        snapshots=snapshots,
        settings=settings,
    )

    await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=_snapshot_payload(edited_bundle),
        ),
    )

    override = execute.handle.call_args.kwargs["command"].version_override
    assert override.bundle_files == edited_bundle
    assert override.bundle_files != saved_bundle
    stored: SandboxSnapshot = snapshots.create.call_args.kwargs["snapshot"]
    assert stored.bundle_files == edited_bundle
    source_only_bytes = len(
        json.dumps({"source_code": _snapshot_payload({}).source_code}, ensure_ascii=False).encode(
            "utf-8"
        )
    )
    bundle_bytes = sum(len(text.encode("utf-8")) for text in edited_bundle.values())
    assert stored.payload_bytes >= source_only_bytes + bundle_bytes


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("bad_name", ["../roster.py", "pkg/roster.py", ".hidden.py", ""])
async def test_run_sandbox_rejects_bundle_names_that_escape_the_bundle_directory(
    bad_name: str,
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    tool_id, version_id = uuid4(), uuid4()
    handler = _run_sandbox_handler(
        actor=actor,
        tool_id=tool_id,
        version_id=version_id,
        now=now,
        execute=execute,
        snapshot_id=uuid4(),
        session_files=session_files,
        locks=locks,
        clock=clock,
        snapshots=snapshots,
        settings=settings,
    )
    _, bundle = gruppgenerator_files()

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                snapshot_payload=_snapshot_payload({**bundle, bad_name: "x = 1\n"}),
            ),
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    snapshots.create.assert_not_awaited()
    execute.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_counts_bundle_files_toward_the_snapshot_size_limit(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    source_code, bundle = gruppgenerator_files()
    settings.SANDBOX_SNAPSHOT_MAX_BYTES = len(source_code.encode("utf-8")) + 1_000
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    tool_id, version_id = uuid4(), uuid4()
    handler = _run_sandbox_handler(
        actor=actor,
        tool_id=tool_id,
        version_id=version_id,
        now=now,
        execute=execute,
        snapshot_id=uuid4(),
        session_files=session_files,
        locks=locks,
        clock=clock,
        snapshots=snapshots,
        settings=settings,
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id, version_id=version_id, snapshot_payload=_snapshot_payload(bundle)
            ),
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    execute.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sandbox_action_reruns_the_snapshot_bundle_not_the_saved_draft(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id, version_id, snapshot_id = uuid4(), uuid4(), uuid4()
    source_code, saved_bundle = gruppgenerator_files()
    edited_bundle = {**saved_bundle, "roster.py": edited_roster_py(saved_bundle["roster.py"])}
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = gruppgenerator_draft(
        version_id=version_id, tool_id=tool_id, created_by_user_id=actor.id, now=now
    )
    versions.list_for_tool.return_value = []
    snapshots.get_by_id.return_value = SandboxSnapshot(
        id=snapshot_id,
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=actor.id,
        entrypoint="run_tool",
        source_code=source_code,
        bundle_files=edited_bundle,
        payload_bytes=1,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    session = make_tool_session(
        tool_id=tool_id, user_id=actor.id, context=f"sandbox:{snapshot_id}", now=now, state_rev=1
    )
    sessions.get.return_value = session
    sessions.update_state.return_value = session
    session_files.list_files.return_value = []
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)
    execute.handle.return_value = ExecuteToolVersionResult(
        run=make_tool_run(
            tool_id=tool_id, version_id=version_id, requested_by_user_id=actor.id, now=now
        ),
        state_update=SetStateUpdate(state={}),
    )
    handler = StartSandboxActionHandler(
        uow=FakeUow(),
        versions=versions,
        maintainers=AsyncMock(spec=ToolMaintainerRepositoryProtocol),
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
            action_id="generate",
            input={},
            expected_state_rev=1,
        ),
    )

    override: ToolVersionOverride = execute.handle.call_args.kwargs["command"].version_override
    assert override.bundle_files == edited_bundle
