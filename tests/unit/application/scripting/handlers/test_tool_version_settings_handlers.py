"""Tests for editor-scoped tool version settings handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.handlers.get_tool_version_settings import (
    GetToolVersionSettingsHandler,
)
from skriptoteket.application.scripting.handlers.update_tool_version_settings import (
    UpdateToolVersionSettingsHandler,
)
from skriptoteket.application.scripting.tool_settings import (
    GetToolVersionSettingsQuery,
    UpdateToolVersionSettingsCommand,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_schema_hash,
    compute_settings_session_context,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField, UiStringField
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_tool_session,
    make_tool_version,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tool_version_settings_without_schema_returns_empty(now) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
        settings_schema=None,
    )

    handler = GetToolVersionSettingsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        query=GetToolVersionSettingsQuery(version_id=version_id),
    )

    assert result.settings.tool_id == tool_id
    assert result.settings.settings_schema is None
    assert result.settings.schema_version is None
    assert result.settings.values == {}
    assert result.settings.state_rev == 0
    sessions.get_or_create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tool_version_settings_with_schema_loads_session(now) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    context = compute_settings_session_context(settings_schema=schema)
    schema_version = compute_settings_schema_hash(settings_schema=schema)

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
        settings_schema=schema,
    )
    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=context,
        now=now,
        state={"theme_color": "#ff00ff"},
        state_rev=2,
    )

    handler = GetToolVersionSettingsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        query=GetToolVersionSettingsQuery(version_id=version_id),
    )

    assert result.settings.tool_id == tool_id
    assert result.settings.schema_version == schema_version
    assert result.settings.settings_schema == schema
    assert result.settings.values == {"theme_color": "#ff00ff"}
    assert result.settings.state_rev == 2
    sessions.get_or_create.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tool_version_settings_requires_tool_maintainer_for_contributors(now) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
        settings_schema=[UiStringField(name="theme_color", label="Färgtema")],
    )
    maintainers.is_maintainer.return_value = False

    handler = GetToolVersionSettingsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=actor, query=GetToolVersionSettingsQuery(version_id=version_id))

    assert exc.value.code is ErrorCode.FORBIDDEN
    sessions.get_or_create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_version_settings_persists_session_state(now) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()
    session_id = uuid4()

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    context = compute_settings_session_context(settings_schema=schema)
    schema_version = compute_settings_schema_hash(settings_schema=schema)

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    versions.get_by_id.return_value = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
        settings_schema=schema,
    )
    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=context,
        now=now,
        state={"theme_color": "#000000"},
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=actor.id,
        context=context,
        now=now,
        state={"theme_color": "#ff00ff"},
        state_rev=1,
    )

    handler = UpdateToolVersionSettingsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        sessions=sessions,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=UpdateToolVersionSettingsCommand(
            version_id=version_id,
            expected_state_rev=0,
            values={"theme_color": "#ff00ff"},
        ),
    )

    assert result.settings.tool_id == tool_id
    assert result.settings.schema_version == schema_version
    assert result.settings.settings_schema == schema
    assert result.settings.values == {"theme_color": "#ff00ff"}
    assert result.settings.state_rev == 1
    sessions.update_state.assert_awaited_once()
