from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from starlette.responses import JSONResponse

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    SaveDraftVersionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
)
from skriptoteket.web.routes import editor
from tests.unit.web.admin_scripting_test_support import _original, _tool, _user, _version


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_version_success_sets_toast_cookie_and_returns_redirect() -> None:
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

    response = await _original(editor.create_draft_version)(
        tool_id=tool.id,
        payload=editor.CreateDraftVersionRequest(
            entrypoint="run_tool",
            source_code="print('hi')",
            change_summary="summary",
            derived_from_version_id=None,
        ),
        handler=handler,
        user=user,
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert "skriptoteket_toast=" in response.headers.get("set-cookie", "")

    data = json.loads(response.body)
    assert data["version_id"] == str(created.id)
    assert data["redirect_url"] == f"/admin/tool-versions/{created.id}"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.entrypoint == "run_tool"
    assert command.source_code == "print('hi')"
    assert command.change_summary == "summary"
    assert command.derived_from_version_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_version_domain_error_returns_ui_message() -> None:
    handler = AsyncMock(spec=CreateDraftVersionHandlerProtocol)
    user = _user(role=Role.ADMIN)
    tool_id = uuid.uuid4()
    handler.handle.side_effect = DomainError(
        code=ErrorCode.FORBIDDEN,
        message="Insufficient permissions",
        details={"tool_id": str(tool_id)},
    )

    response = await _original(editor.create_draft_version)(
        tool_id=tool_id,
        payload=editor.CreateDraftVersionRequest(entrypoint="run_tool", source_code="x"),
        handler=handler,
        user=user,
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 403

    data = json.loads(response.body)
    assert data["error"]["code"] == ErrorCode.FORBIDDEN.value
    assert data["error"]["message"] == "Du saknar behörighet för detta."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_draft_version_success_sets_toast_cookie_and_returns_redirect() -> None:
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

    response = await _original(editor.save_draft_version)(
        version_id=previous.id,
        payload=editor.SaveDraftVersionRequest(
            entrypoint="run_tool",
            source_code="print('new')",
            change_summary=None,
            expected_parent_version_id=previous.id,
        ),
        handler=handler,
        user=user,
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert "skriptoteket_toast=" in response.headers.get("set-cookie", "")

    data = json.loads(response.body)
    assert data["version_id"] == str(saved.id)
    assert data["redirect_url"] == f"/admin/tool-versions/{saved.id}"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.version_id == previous.id
    assert command.expected_parent_version_id == previous.id
    assert command.entrypoint == "run_tool"
    assert command.source_code == "print('new')"
