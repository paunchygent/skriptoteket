from __future__ import annotations

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from skriptoteket.application.catalog.queries import ListAllCategoriesQuery, ListProfessionsQuery
from skriptoteket.application.suggestions.commands import SubmitSuggestionCommand
from skriptoteket.application.suggestions.queries import ListSuggestionsForReviewQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.protocols.catalog import (
    ListAllCategoriesHandlerProtocol,
    ListProfessionsHandlerProtocol,
)
from skriptoteket.protocols.suggestions import (
    ListSuggestionsForReviewHandlerProtocol,
    SubmitSuggestionHandlerProtocol,
)
from skriptoteket.web.auth.dependencies import (
    get_current_session,
    require_admin,
    require_contributor,
)
from skriptoteket.web.templating import templates

router = APIRouter()


@router.get("/suggestions/new", response_class=HTMLResponse)
@inject
async def new_suggestion_page(
    request: Request,
    professions_handler: FromDishka[ListProfessionsHandlerProtocol],
    categories_handler: FromDishka[ListAllCategoriesHandlerProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
    submitted: str | None = None,
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    professions = (await professions_handler.handle(ListProfessionsQuery())).professions
    categories = (await categories_handler.handle(ListAllCategoriesQuery())).categories
    return templates.TemplateResponse(
        "suggestions_new.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "submitted": submitted,
            "error": None,
            "professions": professions,
            "categories": categories,
            "form": {
                "title": "",
                "description": "",
                "profession_slugs": [],
                "category_slugs": [],
            },
        },
    )


@router.post("/suggestions/new")
@inject
async def submit_suggestion(
    request: Request,
    handler: FromDishka[SubmitSuggestionHandlerProtocol],
    professions_handler: FromDishka[ListProfessionsHandlerProtocol],
    categories_handler: FromDishka[ListAllCategoriesHandlerProtocol],
    title: str = Form(...),
    description: str = Form(...),
    profession_slugs: list[str] | None = Form(None),
    category_slugs: list[str] | None = Form(None),
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
) -> RedirectResponse | HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    profession_slugs = profession_slugs or []
    category_slugs = category_slugs or []

    try:
        await handler.handle(
            actor=user,
            command=SubmitSuggestionCommand(
                title=title,
                description=description,
                profession_slugs=profession_slugs,
                category_slugs=category_slugs,
            ),
        )
    except DomainError as exc:
        professions = (await professions_handler.handle(ListProfessionsQuery())).professions
        categories = (await categories_handler.handle(ListAllCategoriesQuery())).categories
        status_code = 400 if exc.code is ErrorCode.VALIDATION_ERROR else 403
        return templates.TemplateResponse(
            "suggestions_new.html",
            {
                "request": request,
                "user": user,
                "csrf_token": csrf_token,
                "submitted": None,
                "error": exc.message,
                "professions": professions,
                "categories": categories,
                "form": {
                    "title": title,
                    "description": description,
                    "profession_slugs": profession_slugs,
                    "category_slugs": category_slugs,
                },
            },
            status_code=status_code,
        )

    return RedirectResponse(url="/suggestions/new?submitted=1", status_code=303)


@router.get("/admin/suggestions", response_class=HTMLResponse)
@inject
async def suggestions_review_queue(
    request: Request,
    handler: FromDishka[ListSuggestionsForReviewHandlerProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    result = await handler.handle(actor=user, query=ListSuggestionsForReviewQuery())
    return templates.TemplateResponse(
        "suggestions_review_queue.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "suggestions": result.suggestions,
        },
    )
