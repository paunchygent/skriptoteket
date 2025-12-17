from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from skriptoteket.application.catalog.commands import (
    AssignMaintainerCommand,
    RemoveMaintainerCommand,
    UpdateToolMetadataCommand,
)
from skriptoteket.application.catalog.queries import ListMaintainersQuery
from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    PublishVersionCommand,
    RequestChangesCommand,
    RollbackVersionCommand,
    SaveDraftVersionCommand,
    SubmitForReviewCommand,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.protocols.catalog import (
    AssignMaintainerHandlerProtocol,
    ListMaintainersHandlerProtocol,
    RemoveMaintainerHandlerProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RollbackVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.auth.dependencies import (
    get_current_session,
    require_admin,
    require_contributor,
    require_superuser,
)
from skriptoteket.web.pages import admin_scripting_support as support
from skriptoteket.web.pages.admin_scripting_runs import router as runs_router
from skriptoteket.web.templating import templates
from skriptoteket.web.toasts import set_toast_cookie
from skriptoteket.web.ui_text import ui_error_message as _ui_error_message

router = APIRouter()

_STARTER_TEMPLATE = """def run_tool(input_path: str, output_dir: str) -> str:
    import os

    size = os.path.getsize(input_path)
    return f"<p>Received file of {size} bytes.</p>"
"""


@router.get("/admin/tools/{tool_id}", response_class=HTMLResponse)
@inject
async def script_editor_for_tool(
    request: Request,
    tool_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    tool = await tools.get_by_id(tool_id=tool_id)
    if tool is None:
        raise not_found("Tool", str(tool_id))

    is_tool_maintainer = await support.require_tool_access(
        actor=user,
        tool_id=tool.id,
        maintainers=maintainers,
    )

    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    selected_version = support.select_default_version(
        actor=user,
        tool=tool,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )

    if selected_version is None:
        entrypoint = "run_tool"
        source_code = _STARTER_TEMPLATE
    else:
        entrypoint = selected_version.entrypoint
        source_code = selected_version.source_code

    return templates.TemplateResponse(
        request=request,
        name="admin/script_editor.html",
        context=support.editor_context(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tool=tool,
            versions=versions,
            selected_version=selected_version,
            editor_entrypoint=entrypoint,
            editor_source_code=source_code,
            run=None,
            error=None,
            is_tool_maintainer=is_tool_maintainer,
        ),
    )


@router.post("/admin/tools/{tool_id}/metadata")
@inject
async def update_tool_metadata(
    request: Request,
    tool_id: UUID,
    handler: FromDishka[UpdateToolMetadataHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
    title: str = Form(...),
    summary: str | None = Form(None),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        await handler.handle(
            actor=user,
            command=UpdateToolMetadataCommand(
                tool_id=tool_id,
                title=title,
                summary=summary,
            ),
        )
    except DomainError as exc:
        tool = await tools.get_by_id(tool_id=tool_id)
        if tool is None:
            raise

        ui_tool = tool.model_copy(update={"title": title, "summary": summary})
        versions = await versions_repo.list_for_tool(tool_id=ui_tool.id, limit=50)
        selected_version = support.select_default_version(
            actor=user, tool=ui_tool, versions=versions, is_tool_maintainer=True
        )

        if selected_version is None:
            editor_entrypoint = "run_tool"
            editor_source_code = _STARTER_TEMPLATE
        else:
            editor_entrypoint = selected_version.entrypoint
            editor_source_code = selected_version.source_code

        return templates.TemplateResponse(
            request=request,
            name="admin/script_editor.html",
            context=support.editor_context(
                request=request,
                user=user,
                csrf_token=csrf_token,
                tool=ui_tool,
                versions=versions,
                selected_version=selected_version,
                editor_entrypoint=editor_entrypoint,
                editor_source_code=editor_source_code,
                run=None,
                error=_ui_error_message(exc),
                is_tool_maintainer=True,
            ),
            status_code=support.status_code_for_error(exc),
        )

    redirect_url = f"/admin/tools/{tool_id}"
    response = support.redirect_with_hx(request=request, url=redirect_url)
    set_toast_cookie(response=response, message="Metadata sparad.", toast_type="success")
    return response


@router.get("/admin/tools/{tool_id}/versions", response_class=HTMLResponse)
@inject
async def version_history(
    request: Request,
    tool_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
) -> HTMLResponse:
    tool = await tools.get_by_id(tool_id=tool_id)
    if tool is None:
        raise not_found("Tool", str(tool_id))

    is_tool_maintainer = await support.require_tool_access(
        actor=user,
        tool_id=tool.id,
        maintainers=maintainers,
    )

    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    visible_versions = support.visible_versions_for_actor(
        actor=user,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/partials/version_list.html",
        context={
            "request": request,
            "user": user,
            "tool": tool,
            "versions": visible_versions,
            "selected_version_id": None,
        },
    )


@router.get("/admin/tool-versions/{version_id}", response_class=HTMLResponse)
@inject
async def script_editor_for_version(
    request: Request,
    version_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""

    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))
    is_tool_maintainer = await support.require_tool_access(
        actor=user,
        tool_id=version.tool_id,
        maintainers=maintainers,
    )

    if not support.is_allowed_to_view_version(
        actor=user,
        version=version,
        is_tool_maintainer=is_tool_maintainer,
    ):
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="Insufficient permissions",
            details={"version_id": str(version.id)},
        )

    tool = await tools.get_by_id(tool_id=version.tool_id)
    if tool is None:
        raise not_found("Tool", str(version.tool_id))

    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    return templates.TemplateResponse(
        request=request,
        name="admin/script_editor.html",
        context=support.editor_context(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tool=tool,
            versions=versions,
            selected_version=version,
            editor_entrypoint=version.entrypoint,
            editor_source_code=version.source_code,
            run=None,
            error=None,
            is_tool_maintainer=is_tool_maintainer,
        ),
    )


@router.post("/admin/tools/{tool_id}/versions")
@inject
async def create_draft(
    request: Request,
    tool_id: UUID,
    handler: FromDishka[CreateDraftVersionHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
    entrypoint: str = Form("run_tool"),
    source_code: str = Form(...),
    change_summary: str | None = Form(None),
    derived_from_version_id: str | None = Form(None),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        derived_from = support.parse_uuid(derived_from_version_id)
        if derived_from_version_id and derived_from is None:
            raise validation_error(
                "Invalid derived_from_version_id",
                details={"derived_from_version_id": derived_from_version_id},
            )
        result = await handler.handle(
            actor=user,
            command=CreateDraftVersionCommand(
                tool_id=tool_id,
                derived_from_version_id=derived_from,
                entrypoint=entrypoint,
                source_code=source_code,
                change_summary=change_summary,
            ),
        )
    except DomainError as exc:
        return await support.render_editor_for_tool_id(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            tool_id=tool_id,
            editor_entrypoint=entrypoint,
            editor_source_code=source_code,
            run=None,
            error=_ui_error_message(exc),
            status_code=support.status_code_for_error(exc),
        )
    redirect_url = f"/admin/tool-versions/{result.version.id}"
    response = support.redirect_with_hx(request=request, url=redirect_url)
    set_toast_cookie(response=response, message="Utkast skapat.", toast_type="success")
    return response


@router.post("/admin/tool-versions/{version_id}/save")
@inject
async def save_draft(
    request: Request,
    version_id: UUID,
    handler: FromDishka[SaveDraftVersionHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
    entrypoint: str = Form("run_tool"),
    source_code: str = Form(...),
    change_summary: str | None = Form(None),
    expected_parent_version_id: str = Form(...),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        expected_parent = support.parse_uuid(expected_parent_version_id)
        if expected_parent is None:
            raise validation_error(
                "Invalid expected_parent_version_id",
                details={"expected_parent_version_id": expected_parent_version_id},
            )
        result = await handler.handle(
            actor=user,
            command=SaveDraftVersionCommand(
                version_id=version_id,
                entrypoint=entrypoint,
                source_code=source_code,
                change_summary=change_summary,
                expected_parent_version_id=expected_parent,
            ),
        )
    except DomainError as exc:
        return await support.render_editor_for_version_id(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            version_id=version_id,
            editor_entrypoint=entrypoint,
            editor_source_code=source_code,
            run=None,
            error=_ui_error_message(exc),
            status_code=support.status_code_for_error(exc),
        )
    redirect_url = f"/admin/tool-versions/{result.version.id}"
    response = support.redirect_with_hx(request=request, url=redirect_url)
    set_toast_cookie(response=response, message="Sparat.", toast_type="success")
    return response


@router.post("/admin/tool-versions/{version_id}/submit-review")
@inject
async def submit_review(
    request: Request,
    version_id: UUID,
    handler: FromDishka[SubmitForReviewHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
    review_note: str | None = Form(None),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        result = await handler.handle(
            actor=user,
            command=SubmitForReviewCommand(version_id=version_id, review_note=review_note),
        )
    except DomainError as exc:
        return await support.render_editor_for_version_id(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            version_id=version_id,
            editor_entrypoint=None,
            editor_source_code=None,
            run=None,
            error=_ui_error_message(exc),
            status_code=support.status_code_for_error(exc),
        )

    redirect_url = f"/admin/tool-versions/{result.version.id}"
    response = support.redirect_with_hx(request=request, url=redirect_url)
    set_toast_cookie(response=response, message="Skickat för granskning.", toast_type="success")
    return response


@router.post("/admin/tool-versions/{version_id}/publish")
@inject
async def publish_version(
    request: Request,
    version_id: UUID,
    handler: FromDishka[PublishVersionHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
    change_summary: str | None = Form(None),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        result = await handler.handle(
            actor=user,
            command=PublishVersionCommand(version_id=version_id, change_summary=change_summary),
        )
    except DomainError as exc:
        return await support.render_editor_for_version_id(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            version_id=version_id,
            editor_entrypoint=None,
            editor_source_code=None,
            run=None,
            error=_ui_error_message(exc),
            status_code=support.status_code_for_error(exc),
        )

    redirect_url = f"/admin/tool-versions/{result.new_active_version.id}"
    response = support.redirect_with_hx(request=request, url=redirect_url)
    set_toast_cookie(response=response, message="Publicerad.", toast_type="success")
    return response


@router.post("/admin/tool-versions/{version_id}/request-changes")
@inject
async def request_changes(
    request: Request,
    version_id: UUID,
    handler: FromDishka[RequestChangesHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
    message: str | None = Form(None),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        result = await handler.handle(
            actor=user,
            command=RequestChangesCommand(version_id=version_id, message=message),
        )
    except DomainError as exc:
        return await support.render_editor_for_version_id(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            version_id=version_id,
            editor_entrypoint=None,
            editor_source_code=None,
            run=None,
            error=_ui_error_message(exc),
            status_code=support.status_code_for_error(exc),
        )

    redirect_url = f"/admin/tool-versions/{result.new_draft_version.id}"
    response = support.redirect_with_hx(request=request, url=redirect_url)
    set_toast_cookie(response=response, message="Ändringar begärda.", toast_type="success")
    return response


# -----------------------------------------------------------------------------
# Maintainer management routes
# -----------------------------------------------------------------------------


@router.get("/admin/tools/{tool_id}/maintainers", response_class=HTMLResponse)
@inject
async def list_maintainers(
    request: Request,
    tool_id: UUID,
    handler: FromDishka[ListMaintainersHandlerProtocol],
    user: User = Depends(require_admin),
) -> HTMLResponse:
    result = await handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/partials/maintainer_list.html",
        context={
            "request": request,
            "tool_id": tool_id,
            "maintainers": result.maintainers,
            "error": None,
        },
    )


@router.post("/admin/tools/{tool_id}/maintainers", response_class=HTMLResponse)
@inject
async def assign_maintainer(
    request: Request,
    tool_id: UUID,
    handler: FromDishka[AssignMaintainerHandlerProtocol],
    list_handler: FromDishka[ListMaintainersHandlerProtocol],
    users: FromDishka[UserRepositoryProtocol],
    user: User = Depends(require_admin),
    user_email: str = Form(...),
) -> HTMLResponse:
    error = None
    try:
        user_auth = await users.get_auth_by_email(email=user_email)
        if user_auth is None:
            error = f"Ingen anvandare med e-post: {user_email}"
        else:
            await handler.handle(
                actor=user,
                command=AssignMaintainerCommand(
                    tool_id=tool_id,
                    user_id=user_auth.user.id,
                ),
            )
    except DomainError as exc:
        error = _ui_error_message(exc)

    # Always return fresh list
    result = await list_handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/partials/maintainer_list.html",
        context={
            "request": request,
            "tool_id": tool_id,
            "maintainers": result.maintainers,
            "error": error,
        },
    )


@router.delete("/admin/tools/{tool_id}/maintainers/{user_id}", response_class=HTMLResponse)
@inject
async def remove_maintainer(
    request: Request,
    tool_id: UUID,
    user_id: UUID,
    handler: FromDishka[RemoveMaintainerHandlerProtocol],
    list_handler: FromDishka[ListMaintainersHandlerProtocol],
    user: User = Depends(require_admin),
) -> HTMLResponse:
    error = None
    try:
        await handler.handle(
            actor=user,
            command=RemoveMaintainerCommand(
                tool_id=tool_id,
                user_id=user_id,
            ),
        )
    except DomainError as exc:
        error = _ui_error_message(exc)

    # Always return fresh list
    result = await list_handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/partials/maintainer_list.html",
        context={
            "request": request,
            "tool_id": tool_id,
            "maintainers": result.maintainers,
            "error": error,
        },
    )


# -----------------------------------------------------------------------------
# Rollback route (superuser only)
# -----------------------------------------------------------------------------


@router.post("/admin/tool-versions/{version_id}/rollback")
@inject
async def rollback_version(
    request: Request,
    version_id: UUID,
    handler: FromDishka[RollbackVersionHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_superuser),
    session: Session | None = Depends(get_current_session),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        result = await handler.handle(
            actor=user,
            command=RollbackVersionCommand(version_id=version_id),
        )
    except DomainError as exc:
        return await support.render_editor_for_version_id(
            request=request,
            user=user,
            csrf_token=csrf_token,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            version_id=version_id,
            editor_entrypoint=None,
            editor_source_code=None,
            run=None,
            error=_ui_error_message(exc),
            status_code=support.status_code_for_error(exc),
        )

    redirect_url = f"/admin/tool-versions/{result.new_active_version.id}"
    return support.redirect_with_hx(request=request, url=redirect_url)


router.include_router(runs_router)
