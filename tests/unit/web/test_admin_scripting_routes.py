from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from unittest.mock import AsyncMock

import pytest
from starlette.responses import RedirectResponse

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    PublishVersionResult,
    RequestChangesResult,
    SaveDraftVersionResult,
    SubmitForReviewResult,
)
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import (
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
)
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.pages import admin_scripting
from tests.unit.web.admin_scripting_test_support import (
    _original,
    _request,
    _session,
    _tool,
    _user,
    _version,
)


@runtime_checkable
class _TemplateProtocol(Protocol):
    name: str


@runtime_checkable
class _TemplateResponseProtocol(Protocol):
    status_code: int
    template: _TemplateProtocol
    context: Mapping[str, object]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_script_editor_for_tool_renders_starter_template_when_no_versions() -> None:
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    tool = _tool(title="No Versions")
    tools.get_by_id.return_value = tool
    versions_repo.list_for_tool.return_value = []

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool.id}")

    response = await _original(admin_scripting.script_editor_for_tool)(
        request=request,
        tool_id=tool.id,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 200
    assert response.template.name == "admin/script_editor.html"
    editor_source_code = response.context["editor_source_code"]
    assert isinstance(editor_source_code, str)
    assert "Received file of" in editor_source_code


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_metadata_success_redirects_with_hx_header() -> None:
    handler = AsyncMock(spec=UpdateToolMetadataHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    tool_id = uuid.uuid4()
    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool_id}", headers={"HX-Request": "true"})

    response = await _original(admin_scripting.update_tool_metadata)(
        request=request,
        tool_id=tool_id,
        handler=handler,
        tools=tools,
        versions_repo=versions_repo,
        user=user,
        session=session,
        title="New Title",
        summary="New Summary",
    )

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/tools/{tool_id}"
    assert response.headers["hx-redirect"] == f"/admin/tools/{tool_id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_tool_metadata_domain_error_renders_editor_with_error() -> None:
    handler = AsyncMock(spec=UpdateToolMetadataHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    tool = _tool(title="Original")
    handler.handle.side_effect = validation_error("Title is required")
    tools.get_by_id.return_value = tool
    versions_repo.list_for_tool.return_value = []

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool.id}")

    response = await _original(admin_scripting.update_tool_metadata)(
        request=request,
        tool_id=tool.id,
        handler=handler,
        tools=tools,
        versions_repo=versions_repo,
        user=user,
        session=session,
        title=" ",
        summary="Summary",
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 400
    assert response.template.name == "admin/script_editor.html"
    tool_in_context = response.context["tool"]
    assert isinstance(tool_in_context, Tool)
    assert tool_in_context.title == " "
    error = response.context["error"]
    assert isinstance(error, str)
    assert error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_version_history_renders_partial_for_admin() -> None:
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    tool = _tool()
    tools.get_by_id.return_value = tool
    versions = [
        _version(tool_id=tool.id, created_by_user_id=uuid.uuid4(), state=VersionState.ACTIVE)
    ]
    versions_repo.list_for_tool.return_value = versions

    user = _user(role=Role.ADMIN)
    request = _request(path=f"/admin/tools/{tool.id}/versions")

    response = await _original(admin_scripting.version_history)(
        request=request,
        tool_id=tool.id,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 200
    assert response.template.name == "admin/partials/version_list.html"
    tool_in_context = response.context["tool"]
    assert isinstance(tool_in_context, Tool)
    assert tool_in_context.id == tool.id
    assert response.context["versions"] == versions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_script_editor_for_version_raises_forbidden_for_other_contributor() -> None:
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    tool = _tool()
    version = _version(
        tool_id=tool.id, created_by_user_id=uuid.uuid4(), state=VersionState.DRAFT, version_number=1
    )
    versions_repo.get_by_id.return_value = version
    tools.get_by_id.return_value = tool

    user = _user(role=Role.CONTRIBUTOR)
    maintainers.is_maintainer.return_value = True
    request = _request(path=f"/admin/tool-versions/{version.id}")

    with pytest.raises(DomainError) as exc_info:
        await _original(admin_scripting.script_editor_for_version)(
            request=request,
            version_id=version.id,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            user=user,
            session=None,
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_script_editor_for_version_renders_editor_when_allowed() -> None:
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.CONTRIBUTOR)
    maintainers.is_maintainer.return_value = True
    tool = _tool()
    version = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
        version_number=1,
    )
    versions_repo.get_by_id.return_value = version
    tools.get_by_id.return_value = tool
    versions_repo.list_for_tool.return_value = [version]

    request = _request(path=f"/admin/tool-versions/{version.id}")
    session = _session(user_id=user.id)

    response = await _original(admin_scripting.script_editor_for_version)(
        request=request,
        version_id=version.id,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 200
    assert response.template.name == "admin/script_editor.html"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_redirects_to_new_version() -> None:
    handler = AsyncMock(spec=CreateDraftVersionHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    maintainers.is_maintainer.return_value = True
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool.id}/versions")

    created_version = _version(
        tool_id=tool.id,
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
    )
    handler.handle.return_value = CreateDraftVersionResult(version=created_version)

    response = await _original(admin_scripting.create_draft)(
        request=request,
        tool_id=tool.id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        entrypoint="run_tool",
        source_code=created_version.source_code,
        change_summary="Initial",
        derived_from_version_id=None,
    )

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == f"/admin/tool-versions/{created_version.id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_invalid_derived_from_uuid_renders_error() -> None:
    handler = AsyncMock(spec=CreateDraftVersionHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    tool = _tool()
    tools.get_by_id.return_value = tool
    versions_repo.list_for_tool.return_value = []

    user = _user(role=Role.CONTRIBUTOR)
    maintainers.is_maintainer.return_value = True
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/tools/{tool.id}/versions")

    response = await _original(admin_scripting.create_draft)(
        request=request,
        tool_id=tool.id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        entrypoint="run_tool",
        source_code=(
            "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
        ),
        change_summary=None,
        derived_from_version_id="not-a-uuid",
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 400
    assert response.template.name == "admin/script_editor.html"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_draft_redirects_to_new_snapshot() -> None:
    handler = AsyncMock(spec=SaveDraftVersionHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.CONTRIBUTOR)
    maintainers.is_maintainer.return_value = True
    session = _session(user_id=user.id)
    request = _request(path="/admin/tool-versions/x/save")

    saved_version = _version(
        tool_id=uuid.uuid4(),
        created_by_user_id=user.id,
        state=VersionState.DRAFT,
    )
    handler.handle.return_value = SaveDraftVersionResult(version=saved_version)

    response = await _original(admin_scripting.save_draft)(
        request=request,
        version_id=saved_version.id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        entrypoint="run_tool",
        source_code=saved_version.source_code,
        change_summary=None,
        expected_parent_version_id=str(uuid.uuid4()),
    )

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == f"/admin/tool-versions/{saved_version.id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_review_redirects_on_success() -> None:
    handler = AsyncMock(spec=SubmitForReviewHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.CONTRIBUTOR)
    maintainers.is_maintainer.return_value = True
    session = _session(user_id=user.id)
    request = _request(path="/admin/tool-versions/x/submit-review")

    reviewed_version = _version(
        tool_id=uuid.uuid4(),
        created_by_user_id=user.id,
        state=VersionState.IN_REVIEW,
    )
    handler.handle.return_value = SubmitForReviewResult(version=reviewed_version)

    response = await _original(admin_scripting.submit_review)(
        request=request,
        version_id=reviewed_version.id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        review_note="Review me",
    )

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == f"/admin/tool-versions/{reviewed_version.id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_version_redirects_on_success() -> None:
    handler = AsyncMock(spec=PublishVersionHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path="/admin/tool-versions/x/publish")

    new_active = _version(
        tool_id=uuid.uuid4(),
        created_by_user_id=user.id,
        state=VersionState.ACTIVE,
    )
    handler.handle.return_value = PublishVersionResult(
        new_active_version=new_active,
        archived_reviewed_version=_version(
            tool_id=new_active.tool_id,
            created_by_user_id=user.id,
            state=VersionState.ARCHIVED,
            version_number=new_active.version_number - 1,
        ),
        archived_previous_active_version=None,
    )

    response = await _original(admin_scripting.publish_version)(
        request=request,
        version_id=new_active.id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        change_summary="Publish",
    )

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == f"/admin/tool-versions/{new_active.id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_changes_redirects_on_success() -> None:
    handler = AsyncMock(spec=RequestChangesHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path="/admin/tool-versions/x/request-changes")

    new_draft = _version(tool_id=uuid.uuid4(), created_by_user_id=user.id, state=VersionState.DRAFT)
    handler.handle.return_value = RequestChangesResult(
        new_draft_version=new_draft,
        archived_in_review_version=_version(
            tool_id=new_draft.tool_id,
            created_by_user_id=user.id,
            state=VersionState.ARCHIVED,
            version_number=new_draft.version_number - 1,
        ),
    )

    response = await _original(admin_scripting.request_changes)(
        request=request,
        version_id=new_draft.id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        message="Fix this",
    )

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == f"/admin/tool-versions/{new_draft.id}"
