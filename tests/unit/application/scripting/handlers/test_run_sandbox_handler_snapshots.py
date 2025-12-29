"""Snapshot-specific tests for RunSandboxHandler."""

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
from skriptoteket.domain.scripting.tool_settings import (
    ToolSettingsSchema,
    compute_sandbox_settings_context,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiStringField
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
async def test_run_sandbox_persists_session_with_correct_context(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    """Verify session uses sandbox:<snapshot_id> context format."""
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
        run=run, normalized_state={"data": "value"}
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

    get_or_create_kwargs = sessions.get_or_create.call_args.kwargs
    assert get_or_create_kwargs["context"] == f"sandbox:{result.snapshot_id}"

    update_kwargs = sessions.update_state.call_args.kwargs
    assert update_kwargs["context"] == f"sandbox:{result.snapshot_id}"
    assert update_kwargs["state"] == {"data": "value"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_creates_snapshot_with_expected_fields(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()
    run_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    payload = make_snapshot_payload().model_copy(update={"usage_instructions": "  Kör  "})

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
            snapshot_payload=payload,
            input_files=[],
        ),
    )

    snapshots.create.assert_awaited_once()
    created_snapshot = snapshots.create.call_args.kwargs["snapshot"]
    assert result.snapshot_id == snapshot_id
    assert created_snapshot.id == snapshot_id
    assert created_snapshot.tool_id == tool_id
    assert created_snapshot.draft_head_id == version_id
    assert created_snapshot.created_by_user_id == actor.id
    assert created_snapshot.entrypoint == payload.entrypoint
    assert created_snapshot.source_code == payload.source_code
    assert created_snapshot.usage_instructions == "Kör"
    assert created_snapshot.payload_bytes > 0
    assert created_snapshot.payload_bytes <= settings.SANDBOX_SNAPSHOT_MAX_BYTES
    assert created_snapshot.created_at == now
    assert created_snapshot.expires_at == now + timedelta(
        seconds=settings.SANDBOX_SNAPSHOT_TTL_SECONDS
    )

    execute.handle.assert_awaited_once()
    execute_kwargs = execute.handle.call_args.kwargs
    execute_command = execute_kwargs["command"]
    assert execute_command.snapshot_id == snapshot_id
    assert execute_command.version_override is not None
    assert execute_command.version_override.entrypoint == payload.entrypoint
    assert execute_command.version_override.source_code == payload.source_code


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_passes_settings_context_override(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()
    run_id = uuid4()

    schema: ToolSettingsSchema = [UiStringField(name="theme_color", label="Färgtema")]
    payload = make_snapshot_payload().model_copy(update={"settings_schema": schema})

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    execute = AsyncMock(spec=ExecuteToolVersionHandlerProtocol)

    id_generator.new_uuid.return_value = snapshot_id
    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
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

    await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=payload,
            input_files=[],
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
async def test_run_sandbox_rejects_oversize_snapshot_payload(
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
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

    settings.SANDBOX_SNAPSHOT_MAX_BYTES = 10

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

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RunSandboxCommand(
                tool_id=tool_id,
                version_id=version_id,
                snapshot_payload=make_snapshot_payload(),
                input_files=[],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    snapshots.create.assert_not_called()
    execute.handle.assert_not_called()
