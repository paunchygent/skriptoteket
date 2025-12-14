from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from skriptoteket.application.catalog.queries import (
    ListCategoriesForProfessionQuery,
    ListProfessionsQuery,
    ListToolsByTagsQuery,
)
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.protocols.catalog import (
    ListCategoriesForProfessionHandlerProtocol,
    ListProfessionsHandlerProtocol,
    ListToolsByTagsHandlerProtocol,
)
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.templating import templates

router = APIRouter(prefix="/browse")


@router.get("/", response_class=HTMLResponse)
@inject
async def list_professions(
    request: Request,
    handler: FromDishka[ListProfessionsHandlerProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    result = await handler.handle(ListProfessionsQuery())
    return templates.TemplateResponse(
        "browse_professions.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "professions": result.professions,
        },
    )


@router.get("/{profession_slug}", response_class=HTMLResponse)
@inject
async def list_categories_for_profession(
    request: Request,
    profession_slug: str,
    handler: FromDishka[ListCategoriesForProfessionHandlerProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    result = await handler.handle(ListCategoriesForProfessionQuery(profession_slug=profession_slug))
    return templates.TemplateResponse(
        "browse_categories.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "profession": result.profession,
            "categories": result.categories,
        },
    )


@router.get("/{profession_slug}/{category_slug}", response_class=HTMLResponse)
@inject
async def list_tools_by_tags(
    request: Request,
    profession_slug: str,
    category_slug: str,
    handler: FromDishka[ListToolsByTagsHandlerProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    result = await handler.handle(
        ListToolsByTagsQuery(profession_slug=profession_slug, category_slug=category_slug)
    )
    return templates.TemplateResponse(
        "browse_tools.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "profession": result.profession,
            "category": result.category,
            "tools": result.tools,
        },
    )
