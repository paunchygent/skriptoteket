from __future__ import annotations

import json
from urllib.parse import unquote
from unittest.mock import AsyncMock, MagicMock

import pytest

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    SaveDraftVersionResult,
)
from skriptoteket.application.catalog.queries import ListToolTaxonomyResult
from skriptoteket.application.catalog.commands import UpdateToolTaxonomyResult
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import (
    ListToolTaxonomyHandlerProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
)
from skriptoteket.web.api.v1 import editor
from tests.unit.web.admin_scripting_test_support import _tool, _user, _version


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


def _decode_toast_payload(value: str) -> dict[str, str]:
    return json.loads(unquote(value))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_version_success_returns_save_result() -> None:
    handler = AsyncMock(spec=CreateDraftVersionHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    created = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=1,
    )
    handler.handle.return_value = CreateDraftVersionResult(version=created)

    mock_response = MagicMock()
    mock_response.set_cookie = MagicMock()

    result = await _unwrap_dishka(editor.create_draft_version)(
        tool_id=tool.id,
        payload=editor.CreateDraftVersionRequest(
            entrypoint="run_tool",
            source_code="print('hi')",
            change_summary="summary",
            derived_from_version_id=None,
        ),
        response=mock_response,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.SaveResult)
    assert result.version_id == created.id
    assert result.redirect_url == f"/admin/tool-versions/{created.id}"

    # Verify toast cookie was set
    mock_response.set_cookie.assert_called_once()
    call_kwargs = mock_response.set_cookie.call_args.kwargs
    assert call_kwargs["key"] == "skriptoteket_toast"
    payload = _decode_toast_payload(call_kwargs["value"])
    assert payload["m"] == "Utkast skapat."
    assert payload["t"] == "success"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.entrypoint == "run_tool"
    assert command.source_code == "print('hi')"
    assert command.change_summary == "summary"
    assert command.derived_from_version_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_draft_version_success_returns_save_result() -> None:
    handler = AsyncMock(spec=SaveDraftVersionHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    previous = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=1,
    )
    saved = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=2,
    )
    handler.handle.return_value = SaveDraftVersionResult(version=saved)

    mock_response = MagicMock()
    mock_response.set_cookie = MagicMock()

    result = await _unwrap_dishka(editor.save_draft_version)(
        version_id=previous.id,
        payload=editor.SaveDraftVersionRequest(
            entrypoint="run_tool",
            source_code="print('new')",
            change_summary=None,
            expected_parent_version_id=previous.id,
        ),
        response=mock_response,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.SaveResult)
    assert result.version_id == saved.id
    assert result.redirect_url == f"/admin/tool-versions/{saved.id}"

    # Verify toast cookie was set
    mock_response.set_cookie.assert_called_once()
    call_kwargs = mock_response.set_cookie.call_args.kwargs
    assert call_kwargs["key"] == "skriptoteket_toast"
    payload = _decode_toast_payload(call_kwargs["value"])
    assert payload["m"] == "Sparat."
    assert payload["t"] == "success"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.version_id == previous.id
    assert command.expected_parent_version_id == previous.id
    assert command.entrypoint == "run_tool"
    assert command.source_code == "print('new')"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tool_taxonomy_returns_response() -> None:
    handler = AsyncMock(spec=ListToolTaxonomyHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    profession_ids = [tool.id]
    category_ids = [tool.id]
    handler.handle.return_value = ListToolTaxonomyResult(
        tool_id=tool.id,
        profession_ids=profession_ids,
        category_ids=category_ids,
    )

    result = await _unwrap_dishka(editor.get_tool_taxonomy)(
        tool_id=tool.id,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.ToolTaxonomyResponse)
    assert result.tool_id == tool.id
    assert result.profession_ids == profession_ids
    assert result.category_ids == category_ids

    handler.handle.assert_awaited_once()
    query = handler.handle.call_args.kwargs["query"]
    assert query.tool_id == tool.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_taxonomy_calls_handler() -> None:
    handler = AsyncMock(spec=UpdateToolTaxonomyHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    profession_ids = [tool.id]
    category_ids = [tool.id]
    handler.handle.return_value = UpdateToolTaxonomyResult(
        tool_id=tool.id,
        profession_ids=profession_ids,
        category_ids=category_ids,
    )

    result = await _unwrap_dishka(editor.update_tool_taxonomy)(
        tool_id=tool.id,
        payload=editor.ToolTaxonomyRequest(
            profession_ids=profession_ids,
            category_ids=category_ids,
        ),
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.ToolTaxonomyResponse)
    assert result.tool_id == tool.id
    assert result.profession_ids == profession_ids
    assert result.category_ids == category_ids

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.profession_ids == profession_ids
    assert command.category_ids == category_ids
