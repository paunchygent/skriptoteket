from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.handlers.delete_sandbox_session_files import (
    DeleteSandboxSessionFilesHandler,
)
from skriptoteket.application.scripting.handlers.delete_session_files import (
    DeleteSessionFilesHandler,
)
from skriptoteket.application.scripting.session_files import (
    DeleteSandboxSessionFilesCommand,
    DeleteSessionFilesCommand,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_sandbox_snapshot,
    make_tool_version,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_session_files_calls_storage(now: datetime) -> None:
    actor = make_user(role=Role.USER)
    tool_id = uuid4()
    tool = make_tool(now=now, tool_id=tool_id, is_published=True).model_copy(
        update={"active_version_id": uuid4()}
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    curated_apps = AsyncMock(spec=CuratedAppRegistryProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)

    tools.get_by_id.return_value = tool
    curated_apps.get_by_tool_id.return_value = None
    session_files.delete_files.return_value = 2

    handler = DeleteSessionFilesHandler(
        uow=uow,
        tools=tools,
        curated_apps=curated_apps,
        session_files=session_files,
    )

    result = await handler.handle(
        actor=actor,
        command=DeleteSessionFilesCommand(
            tool_id=tool_id,
            context=" default ",
            names=["a.txt", "b.txt"],
        ),
    )

    assert result.context == "default"
    assert result.deleted == 2
    session_files.delete_files.assert_awaited_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context="default",
        names=["a.txt", "b.txt"],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_sandbox_session_files_calls_storage(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    snapshot_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    snapshots = AsyncMock(spec=SandboxSnapshotRepositoryProtocol)
    session_files = AsyncMock(spec=SessionFileStorageProtocol)
    clock = Mock(spec=ClockProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    snapshots.get_by_id.return_value = make_sandbox_snapshot(
        snapshot_id=snapshot_id,
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=actor.id,
        now=now,
        expires_at=now + timedelta(hours=1),
    )
    clock.now.return_value = now
    session_files.delete_files.return_value = 1

    handler = DeleteSandboxSessionFilesHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        snapshots=snapshots,
        session_files=session_files,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        command=DeleteSandboxSessionFilesCommand(
            version_id=version_id,
            snapshot_id=snapshot_id,
            names=["old.txt"],
        ),
    )

    assert result.deleted == 1
    session_files.delete_files.assert_awaited_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox-files:{version_id}",
        names=["old.txt"],
    )
