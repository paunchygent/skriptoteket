"""Permission and lock enforcement tests for RunSandboxHandler."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import RunSandboxCommand
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
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
async def test_run_sandbox_contributor_not_maintainer_raises_forbidden(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_user_role_raises_insufficient_permissions(
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    versions.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_requires_active_draft_lock(
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

    assert exc_info.value.code is ErrorCode.CONFLICT
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_rejects_lock_owned_by_another_user(
    now: datetime,
    session_files: AsyncMock,
    locks: AsyncMock,
    clock: Mock,
    snapshots: AsyncMock,
    settings: Mock,
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

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    execute.handle.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_rejects_non_head_draft_version(
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

    assert exc_info.value.code is ErrorCode.CONFLICT
    locks.get_for_tool.assert_not_called()
    execute.handle.assert_not_called()
