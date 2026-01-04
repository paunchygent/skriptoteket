from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.scripting.commands import SchemaName, ValidateToolSchemasCommand
from skriptoteket.application.scripting.handlers.validate_tool_schemas import (
    ValidateToolSchemasHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import FakeUow


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_tool_schemas_requires_maintainer_for_contributor(
    now: datetime,
) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(owner_user_id=actor.id, now=now)

    settings = Mock(spec=Settings)
    settings.UPLOAD_MAX_FILES = 10

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = False

    handler = ValidateToolSchemasHandler(
        settings=settings,
        uow=uow,
        tools=tools,
        maintainers=maintainers,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=ValidateToolSchemasCommand(
                tool_id=tool.id,
                settings_schema=None,
                input_schema=[],
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_tool_schemas_returns_combined_issues_when_both_invalid(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(owner_user_id=actor.id, now=now)

    settings = Mock(spec=Settings)
    settings.UPLOAD_MAX_FILES = 10

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)

    handler = ValidateToolSchemasHandler(
        settings=settings,
        uow=uow,
        tools=tools,
        maintainers=maintainers,
    )

    result = await handler.handle(
        actor=actor,
        command=ValidateToolSchemasCommand(
            tool_id=tool.id,
            settings_schema="nope",
            input_schema=None,
        ),
    )

    messages = {(issue.schema_name, issue.message) for issue in result.issues}
    assert result.valid is False
    assert (SchemaName.INPUT_SCHEMA, "input_schema is required and must be an array") in messages
    assert (SchemaName.SETTINGS_SCHEMA, "settings_schema must be an array or null") in messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_tool_schemas_maps_pydantic_loc_to_path(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(owner_user_id=actor.id, now=now)

    settings = Mock(spec=Settings)
    settings.UPLOAD_MAX_FILES = 10

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)

    handler = ValidateToolSchemasHandler(
        settings=settings,
        uow=uow,
        tools=tools,
        maintainers=maintainers,
    )

    result = await handler.handle(
        actor=actor,
        command=ValidateToolSchemasCommand(
            tool_id=tool.id,
            settings_schema=[],
            input_schema=[
                {
                    "kind": "file",
                    "name": "documents",
                    "label": "Documents",
                    "min": 0,
                }
            ],
        ),
    )

    assert result.valid is False
    assert any(
        issue.schema_name is SchemaName.INPUT_SCHEMA and issue.path == "/0/max"
        for issue in result.issues
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_tool_schemas_enforces_upload_max_files(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(owner_user_id=actor.id, now=now)

    settings = Mock(spec=Settings)
    settings.UPLOAD_MAX_FILES = 10

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)

    handler = ValidateToolSchemasHandler(
        settings=settings,
        uow=uow,
        tools=tools,
        maintainers=maintainers,
    )

    result = await handler.handle(
        actor=actor,
        command=ValidateToolSchemasCommand(
            tool_id=tool.id,
            settings_schema=[],
            input_schema=[
                {
                    "kind": "file",
                    "name": "documents",
                    "label": "Documents",
                    "min": 0,
                    "max": 11,
                }
            ],
        ),
    )

    assert result.valid is False
    assert any(
        issue.schema_name is SchemaName.INPUT_SCHEMA and issue.path == "/0/max"
        for issue in result.issues
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_tool_schemas_maps_domain_validation_error_to_issue(
    now: datetime,
) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(owner_user_id=actor.id, now=now)

    settings = Mock(spec=Settings)
    settings.UPLOAD_MAX_FILES = 10

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)

    handler = ValidateToolSchemasHandler(
        settings=settings,
        uow=uow,
        tools=tools,
        maintainers=maintainers,
    )

    result = await handler.handle(
        actor=actor,
        command=ValidateToolSchemasCommand(
            tool_id=tool.id,
            settings_schema=[],
            input_schema=[
                {"kind": "string", "name": "title", "label": "Title"},
                {"kind": "string", "name": "title", "label": "Title 2"},
            ],
        ),
    )

    assert result.valid is False
    assert any(
        issue.schema_name is SchemaName.INPUT_SCHEMA
        and issue.path is None
        and issue.message == "input_schema contains duplicate field names"
        for issue in result.issues
    )
