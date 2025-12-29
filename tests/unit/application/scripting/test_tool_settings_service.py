from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.tool_settings_service import ToolSettingsService
from skriptoteket.domain.scripting.tool_settings import (
    compute_sandbox_settings_context,
    compute_settings_schema_hash,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField, UiStringField
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.unit.application.scripting.handlers.sandbox_test_support import make_tool_session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_sandbox_settings_ignores_invalid_state(now) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    draft_head_id = uuid4()
    session_id = uuid4()

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    context = compute_sandbox_settings_context(
        draft_head_id=draft_head_id,
        settings_schema=schema,
    )
    schema_version = compute_settings_schema_hash(settings_schema=schema)

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        now=now,
        state={"theme_color": 123},
        state_rev=2,
    )

    service = ToolSettingsService(sessions=sessions, id_generator=id_generator)

    result = await service.resolve_sandbox_settings(
        tool_id=tool_id,
        user_id=user_id,
        draft_head_id=draft_head_id,
        settings_schema=schema,
    )

    assert result.tool_id == tool_id
    assert result.schema_version == schema_version
    assert result.values == {}
    assert result.state_rev == 2
    sessions.get_or_create.assert_awaited_once_with(
        session_id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_sandbox_settings_updates_session(now) -> None:
    tool_id = uuid4()
    user_id = uuid4()
    draft_head_id = uuid4()
    session_id = uuid4()

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    context = compute_sandbox_settings_context(
        draft_head_id=draft_head_id,
        settings_schema=schema,
    )
    schema_version = compute_settings_schema_hash(settings_schema=schema)

    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)

    id_generator.new_uuid.return_value = session_id
    sessions.get_or_create.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        now=now,
        state={},
        state_rev=0,
    )
    sessions.update_state.return_value = make_tool_session(
        session_id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        now=now,
        state={"theme_color": "#ff00ff"},
        state_rev=1,
    )

    service = ToolSettingsService(sessions=sessions, id_generator=id_generator)

    result = await service.save_sandbox_settings(
        tool_id=tool_id,
        user_id=user_id,
        draft_head_id=draft_head_id,
        settings_schema=schema,
        expected_state_rev=0,
        values={"theme_color": "#ff00ff"},
    )

    assert result.tool_id == tool_id
    assert result.schema_version == schema_version
    assert result.values == {"theme_color": "#ff00ff"}
    assert result.state_rev == 1
    sessions.update_state.assert_awaited_once_with(
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        expected_state_rev=0,
        state={"theme_color": "#ff00ff"},
    )
