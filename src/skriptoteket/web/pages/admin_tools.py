from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from skriptoteket.application.catalog.commands import DepublishToolCommand, PublishToolCommand
from skriptoteket.application.catalog.queries import ListToolsForAdminQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.protocols.catalog import (
    DepublishToolHandlerProtocol,
    ListToolsForAdminHandlerProtocol,
    PublishToolHandlerProtocol,
)
from skriptoteket.web.auth.dependencies import get_current_session, require_admin
from skriptoteket.web.templating import templates

router = APIRouter()


@router.get("/admin/tools", response_class=HTMLResponse)
@inject
async def list_tools(
    request: Request,
    handler: FromDishka[ListToolsForAdminHandlerProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
    updated: str | None = None,
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    result = await handler.handle(actor=user, query=ListToolsForAdminQuery())
    return templates.TemplateResponse(
        request=request,
        name="admin_tools.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "updated": updated,
            "error": None,
            "tools": result.tools,
        },
    )


def _status_code_for_error(exc: DomainError) -> int:
    if exc.code is ErrorCode.NOT_FOUND:
        return 404
    if exc.code is ErrorCode.FORBIDDEN:
        return 403
    if exc.code is ErrorCode.CONFLICT:
        return 409
    if exc.code is ErrorCode.VALIDATION_ERROR:
        return 400
    return 500


@router.post("/admin/tools/{tool_id}/publish")
@inject
async def publish_tool(
    request: Request,
    tool_id: UUID,
    publish_handler: FromDishka[PublishToolHandlerProtocol],
    list_handler: FromDishka[ListToolsForAdminHandlerProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        await publish_handler.handle(actor=user, command=PublishToolCommand(tool_id=tool_id))
    except DomainError as exc:
        result = await list_handler.handle(actor=user, query=ListToolsForAdminQuery())
        return templates.TemplateResponse(
            request=request,
            name="admin_tools.html",
            context={
                "request": request,
                "user": user,
                "csrf_token": csrf_token,
                "updated": None,
                "error": exc.message,
                "tools": result.tools,
            },
            status_code=_status_code_for_error(exc),
        )
    return RedirectResponse(url="/admin/tools?updated=1", status_code=303)


@router.post("/admin/tools/{tool_id}/depublish")
@inject
async def depublish_tool(
    request: Request,
    tool_id: UUID,
    depublish_handler: FromDishka[DepublishToolHandlerProtocol],
    list_handler: FromDishka[ListToolsForAdminHandlerProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    try:
        await depublish_handler.handle(actor=user, command=DepublishToolCommand(tool_id=tool_id))
    except DomainError as exc:
        result = await list_handler.handle(actor=user, query=ListToolsForAdminQuery())
        return templates.TemplateResponse(
            request=request,
            name="admin_tools.html",
            context={
                "request": request,
                "user": user,
                "csrf_token": csrf_token,
                "updated": None,
                "error": exc.message,
                "tools": result.tools,
            },
            status_code=_status_code_for_error(exc),
        )
    return RedirectResponse(url="/admin/tools?updated=1", status_code=303)
