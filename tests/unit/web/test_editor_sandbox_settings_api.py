"""Tests for editor sandbox settings endpoints (ST-14-05/08)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.tool_settings import (
    ResolveSandboxSettingsResult,
    SaveSandboxSettingsResult,
    ToolSettingsState,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField, UiStringField
from skriptoteket.protocols.tool_settings import (
    ResolveSandboxSettingsHandlerProtocol,
    SaveSandboxSettingsHandlerProtocol,
)
from skriptoteket.web.api.v1 import editor
from tests.unit.web.admin_scripting_test_support import _user


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_sandbox_settings_calls_handler() -> None:
    handler = AsyncMock(spec=ResolveSandboxSettingsHandlerProtocol)
    user = _user(role=Role.CONTRIBUTOR)
    version_id = uuid4()

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    settings_state = ToolSettingsState(
        tool_id=uuid4(),
        schema_version="schema-hash",
        settings_schema=schema,
        values={"theme_color": "#ff00ff"},
        state_rev=2,
    )
    handler.handle.return_value = ResolveSandboxSettingsResult(settings=settings_state)

    result = await _unwrap_dishka(editor.resolve_sandbox_settings)(
        version_id=version_id,
        payload=editor.SandboxSettingsResolveRequest(settings_schema=schema),
        handler=handler,
        user=user,
        _=None,
    )

    assert isinstance(result, editor.SandboxSettingsResponse)
    assert result.values == {"theme_color": "#ff00ff"}
    handler.handle.assert_awaited_once()
    assert handler.handle.call_args.kwargs["query"].version_id == version_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_sandbox_settings_calls_handler() -> None:
    handler = AsyncMock(spec=SaveSandboxSettingsHandlerProtocol)
    user = _user(role=Role.CONTRIBUTOR)
    version_id = uuid4()

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    settings_state = ToolSettingsState(
        tool_id=uuid4(),
        schema_version="schema-hash",
        settings_schema=schema,
        values={"theme_color": "#000000"},
        state_rev=3,
    )
    handler.handle.return_value = SaveSandboxSettingsResult(settings=settings_state)

    result = await _unwrap_dishka(editor.save_sandbox_settings)(
        version_id=version_id,
        payload=editor.SandboxSettingsSaveRequest(
            settings_schema=schema,
            expected_state_rev=2,
            values={"theme_color": "#000000"},
        ),
        handler=handler,
        user=user,
        _=None,
    )

    assert isinstance(result, editor.SandboxSettingsResponse)
    assert result.state_rev == 3
    handler.handle.assert_awaited_once()
    assert handler.handle.call_args.kwargs["command"].version_id == version_id
