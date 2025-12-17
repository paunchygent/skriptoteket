"""Contributor tool management routes.

Routes for contributors to view and access tools they maintain.
"""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from skriptoteket.application.catalog.queries import ListToolsForContributorQuery
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.protocols.catalog import ListToolsForContributorHandlerProtocol
from skriptoteket.web.auth.dependencies import get_current_session, require_contributor
from skriptoteket.web.templating import templates

router = APIRouter()


@router.get("/my-tools", response_class=HTMLResponse)
@inject
async def my_tools(
    request: Request,
    handler: FromDishka[ListToolsForContributorHandlerProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    """List all tools that the current contributor maintains."""
    csrf_token = session.csrf_token if session else ""
    result = await handler.handle(
        actor=user,
        query=ListToolsForContributorQuery(),
    )
    return templates.TemplateResponse(
        request=request,
        name="my_tools.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "tools": result.tools,
        },
    )
