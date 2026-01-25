from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.file_refs import (
    ListSandboxFileRefsQuery,
    ListToolFileRefsQuery,
)
from skriptoteket.application.scripting.handlers.list_sandbox_file_refs import (
    ListSandboxFileRefsHandler,
)
from skriptoteket.application.scripting.handlers.list_tool_file_refs import (
    ListToolFileRefsHandler,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.file_refs import FileRefEntry, FileRefResolverProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    make_sandbox_snapshot,
    make_tool_version,
)


class FakeUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> UnitOfWorkProtocol:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tool_file_refs_returns_expected_shape(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    tool = make_tool(now=now, is_published=True).model_copy(update={"active_version_id": uuid4()})

    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.get_by_tool_id.return_value = None
    file_refs = AsyncMock(spec=FileRefResolverProtocol)
    file_refs.list_refs.return_value = [
        FileRefEntry(ref="session:doc.txt", name="doc.txt", bytes=4, field="documents")
    ]

    handler = ListToolFileRefsHandler(
        uow=FakeUow(),
        tools=tools,
        curated_apps=curated_apps,
        file_refs=file_refs,
    )

    result = await handler.handle(
        actor=actor,
        query=ListToolFileRefsQuery(tool_id=tool.id, context=" default "),
    )

    assert result.context == "default"
    file_refs.list_refs.assert_awaited_once_with(
        tool_id=tool.id,
        user_id=actor.id,
        context="default",
    )
    payload = result.files[0].model_dump()
    assert set(payload.keys()) == {"ref", "name", "bytes", "field"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_sandbox_file_refs_returns_expected_shape(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN, user_id=uuid4())
    tool_id = uuid4()
    version = make_tool_version(
        version_id=uuid4(),
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    snapshot = make_sandbox_snapshot(
        snapshot_id=uuid4(),
        tool_id=tool_id,
        draft_head_id=version.id,
        created_by_user_id=actor.id,
        now=now,
    )

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    snapshots = AsyncMock(spec=SandboxSnapshotRepositoryProtocol)
    snapshots.get_by_id.return_value = snapshot
    file_refs = AsyncMock(spec=FileRefResolverProtocol)
    file_refs.list_refs.return_value = [
        FileRefEntry(ref="session:photo.png", name="photo.png", bytes=12, field="images")
    ]
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ListSandboxFileRefsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        snapshots=snapshots,
        file_refs=file_refs,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        query=ListSandboxFileRefsQuery(
            version_id=version.id,
            snapshot_id=snapshot.id,
        ),
    )

    assert result.tool_id == tool_id
    assert result.snapshot_id == snapshot.id
    file_refs.list_refs.assert_awaited_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context=f"sandbox-files:{version.id}",
    )
    payload = result.files[0].model_dump()
    assert set(payload.keys()) == {"ref", "name", "bytes", "field"}
