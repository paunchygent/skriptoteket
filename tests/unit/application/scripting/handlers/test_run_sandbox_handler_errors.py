"""Error-path tests for RunSandboxHandler."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import RunSandboxCommand
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
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
    make_tool_version,
)

pytest_plugins = [
    "tests.unit.application.scripting.handlers.run_sandbox_fixtures",
    "tests.unit.application.scripting.handlers.sandbox_handler_fixtures",
]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_when_version_not_found_raises_not_found(
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
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
    snapshots: AsyncMock,
    settings: Mock,
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
                input_files=[("input.txt", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_rejects_blank_entrypoint(
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

    payload = make_snapshot_payload().model_copy(update={"entrypoint": "  "})

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
                snapshot_payload=payload,
                input_files=[("input.txt", b"test")],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    versions.get_by_id.assert_not_called()
    snapshots.create.assert_not_called()
    execute.handle.assert_not_called()
