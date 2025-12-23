from __future__ import annotations

import json
from urllib.parse import unquote
from unittest.mock import AsyncMock, MagicMock

import pytest

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    PublishVersionResult,
    RequestChangesResult,
    RollbackVersionResult,
    SaveDraftVersionResult,
    SubmitForReviewResult,
)
from skriptoteket.application.catalog.queries import ListToolTaxonomyResult
from skriptoteket.application.catalog.commands import (
    UpdateToolMetadataResult,
    UpdateToolTaxonomyResult,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import (
    ListToolTaxonomyHandlerProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RollbackVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
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
async def test_submit_review_returns_workflow_action_response() -> None:
    handler = AsyncMock(spec=SubmitForReviewHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=1,
    )
    handler.handle.return_value = SubmitForReviewResult(version=version)

    mock_response = MagicMock()
    mock_response.set_cookie = MagicMock()

    result = await _unwrap_dishka(editor.submit_review)(
        version_id=version.id,
        payload=editor.SubmitReviewRequest(review_note="Review note"),
        response=mock_response,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == version.id
    assert result.redirect_url == f"/admin/tool-versions/{version.id}"

    mock_response.set_cookie.assert_called_once()
    call_kwargs = mock_response.set_cookie.call_args.kwargs
    assert call_kwargs["key"] == "skriptoteket_toast"
    payload = _decode_toast_payload(call_kwargs["value"])
    assert payload["m"] == "Skickat för granskning."
    assert payload["t"] == "success"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.version_id == version.id
    assert command.review_note == "Review note"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_version_returns_workflow_action_response() -> None:
    handler = AsyncMock(spec=PublishVersionHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    reviewed = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.IN_REVIEW,
        version_number=2,
    )
    new_active = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
        version_number=3,
    )
    handler.handle.return_value = PublishVersionResult(
        new_active_version=new_active,
        archived_reviewed_version=reviewed,
        archived_previous_active_version=None,
    )

    mock_response = MagicMock()
    mock_response.set_cookie = MagicMock()

    result = await _unwrap_dishka(editor.publish_version)(
        version_id=reviewed.id,
        payload=editor.PublishVersionRequest(change_summary="Summary"),
        response=mock_response,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == new_active.id
    assert result.redirect_url == f"/admin/tool-versions/{new_active.id}"

    mock_response.set_cookie.assert_called_once()
    call_kwargs = mock_response.set_cookie.call_args.kwargs
    assert call_kwargs["key"] == "skriptoteket_toast"
    payload = _decode_toast_payload(call_kwargs["value"])
    assert payload["m"] == "Version publicerad."
    assert payload["t"] == "success"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.version_id == reviewed.id
    assert command.change_summary == "Summary"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_changes_returns_workflow_action_response() -> None:
    handler = AsyncMock(spec=RequestChangesHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    reviewed = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.IN_REVIEW,
        version_number=2,
    )
    new_draft = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=3,
    )
    handler.handle.return_value = RequestChangesResult(
        new_draft_version=new_draft,
        archived_in_review_version=reviewed,
    )

    mock_response = MagicMock()
    mock_response.set_cookie = MagicMock()

    result = await _unwrap_dishka(editor.request_changes)(
        version_id=reviewed.id,
        payload=editor.RequestChangesRequest(message="Please adjust"),
        response=mock_response,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == new_draft.id
    assert result.redirect_url == f"/admin/tool-versions/{new_draft.id}"

    mock_response.set_cookie.assert_called_once()
    call_kwargs = mock_response.set_cookie.call_args.kwargs
    assert call_kwargs["key"] == "skriptoteket_toast"
    payload = _decode_toast_payload(call_kwargs["value"])
    assert payload["m"] == "Ändringar begärda."
    assert payload["t"] == "success"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.version_id == reviewed.id
    assert command.message == "Please adjust"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rollback_version_returns_workflow_action_response() -> None:
    handler = AsyncMock(spec=RollbackVersionHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.SUPERUSER)
    archived = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ARCHIVED,
        version_number=1,
    )
    new_active = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
        version_number=5,
    )
    handler.handle.return_value = RollbackVersionResult(
        new_active_version=new_active,
        archived_previous_active_version=None,
    )

    mock_response = MagicMock()
    mock_response.set_cookie = MagicMock()

    result = await _unwrap_dishka(editor.rollback_version)(
        version_id=archived.id,
        response=mock_response,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == new_active.id
    assert result.redirect_url == f"/admin/tool-versions/{new_active.id}"

    mock_response.set_cookie.assert_called_once()
    call_kwargs = mock_response.set_cookie.call_args.kwargs
    assert call_kwargs["key"] == "skriptoteket_toast"
    payload = _decode_toast_payload(call_kwargs["value"])
    assert payload["m"] == f"Återställd till v{new_active.version_number}."
    assert payload["t"] == "success"

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.version_id == archived.id


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_metadata_calls_handler_and_returns_response() -> None:
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    handler = AsyncMock(spec=UpdateToolMetadataHandlerProtocol)
    updated = _tool(title="Normalized title")
    updated = updated.model_copy(update={"summary": "Normalized summary"})
    user = _user(role=Role.ADMIN)
    handler.handle.return_value = UpdateToolMetadataResult(tool=updated)

    result = await _unwrap_dishka(editor.update_tool_metadata)(
        tool_id=updated.id,
        payload=editor.EditorToolMetadataRequest(
            title=" New title ",
            summary=" New summary ",
        ),
        tools=tools_repo,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.EditorToolMetadataResponse)
    assert result.id == updated.id
    assert result.slug == updated.slug
    assert result.title == updated.title
    assert result.summary == updated.summary

    tools_repo.get_by_id.assert_not_awaited()

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == updated.id
    assert command.title == " New title "
    assert command.summary == " New summary "


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_metadata_without_summary_keeps_existing() -> None:
    tools_repo = AsyncMock(spec=ToolRepositoryProtocol)
    handler = AsyncMock(spec=UpdateToolMetadataHandlerProtocol)
    existing = _tool(title="Existing title")
    existing = existing.model_copy(update={"summary": "Existing summary"})
    updated = existing.model_copy(update={"title": "Updated title"})
    user = _user(role=Role.ADMIN)
    tools_repo.get_by_id.return_value = existing
    handler.handle.return_value = UpdateToolMetadataResult(tool=updated)

    result = await _unwrap_dishka(editor.update_tool_metadata)(
        tool_id=existing.id,
        payload=editor.EditorToolMetadataRequest(title="Updated title"),
        tools=tools_repo,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.EditorToolMetadataResponse)
    assert result.id == updated.id
    assert result.title == updated.title
    assert result.summary == updated.summary

    tools_repo.get_by_id.assert_awaited_once_with(tool_id=existing.id)

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == existing.id
    assert command.title == "Updated title"
    assert command.summary == existing.summary
