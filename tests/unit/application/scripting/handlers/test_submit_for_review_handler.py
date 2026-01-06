from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import SubmitForReviewCommand
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_tool_version,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_for_review_rejects_placeholder_slug(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers_repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(now=now, slug=f"draft-{uuid4()}")
    version = make_tool_version(now=now, tool_id=tool.id, created_by_user_id=actor.id)

    tools_repo.get_by_id.return_value = tool
    versions_repo.get_by_id.return_value = version
    maintainers_repo.is_maintainer.return_value = True

    handler = SubmitForReviewHandler(
        uow=uow,
        tools=tools_repo,
        versions=versions_repo,
        maintainers=maintainers_repo,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=SubmitForReviewCommand(version_id=version.id))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    tools_repo.list_tag_ids.assert_not_called()
    versions_repo.update.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_for_review_rejects_missing_taxonomy(now: datetime) -> None:
    uow = FakeUow()
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers_repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(now=now, slug="valid-tool")
    version = make_tool_version(now=now, tool_id=tool.id, created_by_user_id=actor.id)

    tools_repo.get_by_id.return_value = tool
    tools_repo.list_tag_ids.return_value = ([], [uuid4()])
    versions_repo.get_by_id.return_value = version
    maintainers_repo.is_maintainer.return_value = True

    handler = SubmitForReviewHandler(
        uow=uow,
        tools=tools_repo,
        versions=versions_repo,
        maintainers=maintainers_repo,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, command=SubmitForReviewCommand(version_id=version.id))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    tools_repo.list_tag_ids.assert_awaited_once_with(tool_id=tool.id)
    versions_repo.update.assert_not_called()
