from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.commands import UpdateToolTaxonomyCommand
from skriptoteket.application.catalog.handlers.update_tool_taxonomy import (
    UpdateToolTaxonomyHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.catalog_fixtures import make_category, make_profession, make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(now=now)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = UpdateToolTaxonomyHandler(
        uow=uow,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolTaxonomyCommand(
                tool_id=tool.id,
                profession_ids=[uuid4()],
                category_ids=[uuid4()],
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    tools.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_rejects_empty_professions(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = UpdateToolTaxonomyHandler(
        uow=uow,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolTaxonomyCommand(
                tool_id=tool.id,
                profession_ids=[],
                category_ids=[uuid4()],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert uow.entered is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_rejects_duplicate_category_ids(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    category_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = UpdateToolTaxonomyHandler(
        uow=uow,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolTaxonomyCommand(
                tool_id=tool.id,
                profession_ids=[uuid4()],
                category_ids=[category_id, category_id],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert uow.entered is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_rejects_missing_tool(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = UpdateToolTaxonomyHandler(
        uow=uow,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolTaxonomyCommand(
                tool_id=tool_id,
                profession_ids=[uuid4()],
                category_ids=[uuid4()],
            ),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    tools.replace_tags.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_rejects_unknown_profession_id(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    profession_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.list_by_ids.return_value = []

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = UpdateToolTaxonomyHandler(
        uow=uow,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=UpdateToolTaxonomyCommand(
                tool_id=tool.id,
                profession_ids=[profession_id],
                category_ids=[uuid4()],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert uow.entered is True
    assert uow.exited is True
    categories.list_by_ids.assert_not_called()
    tools.replace_tags.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_updates_tags(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    profession = make_profession(now=now)
    category = make_category(now=now)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.list_by_ids.return_value = [profession]

    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    categories.list_by_ids.return_value = [category]

    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = UpdateToolTaxonomyHandler(
        uow=uow,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        command=UpdateToolTaxonomyCommand(
            tool_id=tool.id,
            profession_ids=[profession.id],
            category_ids=[category.id],
        ),
    )

    assert result.tool_id == tool.id
    assert result.profession_ids == [profession.id]
    assert result.category_ids == [category.id]
    tools.replace_tags.assert_awaited_once_with(
        tool_id=tool.id,
        profession_ids=[profession.id],
        category_ids=[category.id],
        now=now,
    )
    assert uow.entered is True
    assert uow.exited is True
