from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import CreateDraftVersionCommand
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_tool_version,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_version_requires_active_lock_when_draft_exists(
    now: datetime,
) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(owner_user_id=actor.id, now=now)
    draft_head = make_tool_version(
        tool_id=tool.id,
        now=now,
        created_by_user_id=actor.id,
    )

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.list_for_tool.return_value = [draft_head]
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = None

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    handler = CreateDraftVersionHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        versions=versions,
        locks=locks,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=CreateDraftVersionCommand(
                tool_id=tool.id,
                entrypoint="run_tool",
                source_code="print('hi')",
                derived_from_version_id=None,
                change_summary=None,
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_version_allows_when_no_draft_head(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(owner_user_id=actor.id, now=now)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.list_for_tool.return_value = []
    versions.get_next_version_number.return_value = 1
    versions.create.side_effect = lambda *, version: version
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    new_version_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = new_version_id

    handler = CreateDraftVersionHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        versions=versions,
        locks=locks,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=CreateDraftVersionCommand(
            tool_id=tool.id,
            entrypoint="run_tool",
            source_code="print('hi')",
            derived_from_version_id=None,
            change_summary=None,
        ),
    )

    assert result.version.id == new_version_id
    versions.create.assert_awaited_once()
