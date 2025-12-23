from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.catalog.commands import (
    UpdateToolMetadataResult,
    UpdateToolTaxonomyResult,
)
from skriptoteket.application.catalog.queries import ListMaintainersResult, ListToolTaxonomyResult
from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    PublishVersionResult,
    RequestChangesResult,
    RollbackVersionResult,
    SaveDraftVersionResult,
    SubmitForReviewResult,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import Role, UserAuth
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import (
    AssignMaintainerHandlerProtocol,
    ListMaintainersHandlerProtocol,
    ListToolTaxonomyHandlerProtocol,
    RemoveMaintainerHandlerProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
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

    result = await _unwrap_dishka(editor.create_draft_version)(
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

    assert isinstance(result, editor.SaveResult)
    assert result.version_id == created.id
    assert result.redirect_url == f"/admin/tool-versions/{created.id}"

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

    result = await _unwrap_dishka(editor.save_draft_version)(
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

    assert isinstance(result, editor.SaveResult)
    assert result.version_id == saved.id
    assert result.redirect_url == f"/admin/tool-versions/{saved.id}"

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

    result = await _unwrap_dishka(editor.submit_review)(
        version_id=version.id,
        payload=editor.SubmitReviewRequest(review_note="Review note"),
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == version.id
    assert result.redirect_url == f"/admin/tool-versions/{version.id}"

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

    result = await _unwrap_dishka(editor.publish_version)(
        version_id=reviewed.id,
        payload=editor.PublishVersionRequest(change_summary="Summary"),
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == new_active.id
    assert result.redirect_url == f"/admin/tool-versions/{new_active.id}"

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

    result = await _unwrap_dishka(editor.request_changes)(
        version_id=reviewed.id,
        payload=editor.RequestChangesRequest(message="Please adjust"),
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == new_draft.id
    assert result.redirect_url == f"/admin/tool-versions/{new_draft.id}"

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

    result = await _unwrap_dishka(editor.rollback_version)(
        version_id=archived.id,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.WorkflowActionResponse)
    assert result.version_id == new_active.id
    assert result.redirect_url == f"/admin/tool-versions/{new_active.id}"

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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tool_maintainers_returns_response() -> None:
    handler = AsyncMock(spec=ListMaintainersHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    maintainer = _user(role=Role.CONTRIBUTOR)
    handler.handle.return_value = ListMaintainersResult(
        tool_id=tool.id,
        maintainers=[maintainer],
    )

    result = await _unwrap_dishka(editor.list_tool_maintainers)(
        tool_id=tool.id,
        handler=handler,
        user=user,
    )

    assert isinstance(result, editor.MaintainerListResponse)
    assert result.tool_id == tool.id
    assert len(result.maintainers) == 1
    assert result.maintainers[0].id == maintainer.id
    assert result.maintainers[0].email == maintainer.email
    assert result.maintainers[0].role == maintainer.role

    handler.handle.assert_awaited_once()
    query = handler.handle.call_args.kwargs["query"]
    assert query.tool_id == tool.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_tool_maintainer_uses_email_lookup_and_returns_list() -> None:
    handler = AsyncMock(spec=AssignMaintainerHandlerProtocol)
    list_handler = AsyncMock(spec=ListMaintainersHandlerProtocol)
    users_repo = AsyncMock(spec=UserRepositoryProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    maintainer = _user(role=Role.CONTRIBUTOR)
    users_repo.get_auth_by_email.return_value = UserAuth(user=maintainer, password_hash=None)
    list_handler.handle.return_value = ListMaintainersResult(
        tool_id=tool.id,
        maintainers=[maintainer],
    )

    result = await _unwrap_dishka(editor.assign_tool_maintainer)(
        tool_id=tool.id,
        payload=editor.AssignMaintainerRequest(email=f" {maintainer.email} "),
        handler=handler,
        list_handler=list_handler,
        users=users_repo,
        user=user,
    )

    assert isinstance(result, editor.MaintainerListResponse)
    assert result.tool_id == tool.id
    assert result.maintainers[0].email == maintainer.email

    users_repo.get_auth_by_email.assert_awaited_once_with(email=maintainer.email)

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.user_id == maintainer.id

    list_handler.handle.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_tool_maintainer_requires_email() -> None:
    handler = AsyncMock(spec=AssignMaintainerHandlerProtocol)
    list_handler = AsyncMock(spec=ListMaintainersHandlerProtocol)
    users_repo = AsyncMock(spec=UserRepositoryProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)

    with pytest.raises(DomainError):
        await _unwrap_dishka(editor.assign_tool_maintainer)(
            tool_id=tool.id,
            payload=editor.AssignMaintainerRequest(email=" "),
            handler=handler,
            list_handler=list_handler,
            users=users_repo,
            user=user,
        )

    handler.handle.assert_not_awaited()
    list_handler.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_tool_maintainer_returns_list() -> None:
    handler = AsyncMock(spec=RemoveMaintainerHandlerProtocol)
    list_handler = AsyncMock(spec=ListMaintainersHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.ADMIN)
    maintainer = _user(role=Role.CONTRIBUTOR)
    list_handler.handle.return_value = ListMaintainersResult(
        tool_id=tool.id,
        maintainers=[maintainer],
    )

    result = await _unwrap_dishka(editor.remove_tool_maintainer)(
        tool_id=tool.id,
        user_id=maintainer.id,
        handler=handler,
        list_handler=list_handler,
        user=user,
    )

    assert isinstance(result, editor.MaintainerListResponse)
    assert result.tool_id == tool.id
    assert result.maintainers[0].id == maintainer.id

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.user_id == maintainer.id

    list_handler.handle.assert_awaited_once()
