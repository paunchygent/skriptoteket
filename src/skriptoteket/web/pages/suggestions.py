from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from skriptoteket.application.catalog.queries import ListAllCategoriesQuery, ListProfessionsQuery
from skriptoteket.application.suggestions.commands import (
    DecideSuggestionCommand,
    SubmitSuggestionCommand,
)
from skriptoteket.application.suggestions.queries import (
    GetSuggestionForReviewQuery,
    ListSuggestionsForReviewQuery,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.domain.suggestions.models import SuggestionDecisionType, SuggestionStatus
from skriptoteket.protocols.catalog import (
    ListAllCategoriesHandlerProtocol,
    ListProfessionsHandlerProtocol,
)
from skriptoteket.protocols.suggestions import (
    DecideSuggestionHandlerProtocol,
    GetSuggestionForReviewHandlerProtocol,
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
        request=request,
        name="suggestions_new.html",
        context={
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
) -> Response:
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
            request=request,
            name="suggestions_new.html",
            context={
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
        request=request,
        name="suggestions_review_queue.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "suggestions": result.suggestions,
        },
    )


@router.get("/admin/suggestions/{suggestion_id}", response_class=HTMLResponse)
@inject
async def suggestion_review_detail(
    request: Request,
    suggestion_id: UUID,
    handler: FromDishka[GetSuggestionForReviewHandlerProtocol],
    professions_handler: FromDishka[ListProfessionsHandlerProtocol],
    categories_handler: FromDishka[ListAllCategoriesHandlerProtocol],
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
    saved: str | None = None,
) -> HTMLResponse:
    csrf_token = session.csrf_token if session else ""
    professions = (await professions_handler.handle(ListProfessionsQuery())).professions
    categories = (await categories_handler.handle(ListAllCategoriesQuery())).categories

    try:
        result = await handler.handle(
            actor=user,
            query=GetSuggestionForReviewQuery(suggestion_id=suggestion_id),
        )
    except DomainError as exc:
        status_code = 404 if exc.code is ErrorCode.NOT_FOUND else 403
        return templates.TemplateResponse(
            request=request,
            name="suggestions_review_detail.html",
            context={
                "request": request,
                "user": user,
                "csrf_token": csrf_token,
                "saved": None,
                "error": exc.message,
                "suggestion": None,
                "decisions": [],
                "professions": professions,
                "categories": categories,
                "form": {},
                "can_decide": False,
            },
            status_code=status_code,
        )

    suggestion = result.suggestion
    return templates.TemplateResponse(
        request=request,
        name="suggestions_review_detail.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "saved": saved,
            "error": None,
            "suggestion": suggestion,
            "decisions": result.decisions,
            "professions": professions,
            "categories": categories,
            "form": {
                "title": suggestion.title,
                "description": suggestion.description,
                "profession_slugs": list(suggestion.profession_slugs),
                "category_slugs": list(suggestion.category_slugs),
                "rationale": "",
                "decision": "accept",
            },
            "can_decide": suggestion.status == SuggestionStatus.PENDING_REVIEW,
        },
    )


@router.post("/admin/suggestions/{suggestion_id}/decision")
@inject
async def decide_suggestion(
    request: Request,
    suggestion_id: UUID,
    handler: FromDishka[DecideSuggestionHandlerProtocol],
    professions_handler: FromDishka[ListProfessionsHandlerProtocol],
    categories_handler: FromDishka[ListAllCategoriesHandlerProtocol],
    review_query_handler: FromDishka[GetSuggestionForReviewHandlerProtocol],
    decision: str = Form(...),
    rationale: str = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    profession_slugs: list[str] | None = Form(None),
    category_slugs: list[str] | None = Form(None),
    user: User = Depends(require_admin),
    session: Session | None = Depends(get_current_session),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    professions = (await professions_handler.handle(ListProfessionsQuery())).professions
    categories = (await categories_handler.handle(ListAllCategoriesQuery())).categories

    try:
        parsed_decision = SuggestionDecisionType(decision)
    except ValueError:
        parsed_decision = SuggestionDecisionType.DENY

    if parsed_decision is SuggestionDecisionType.DENY:
        title = None
        description = None
        profession_slugs = None
        category_slugs = None

    try:
        await handler.handle(
            actor=user,
            command=DecideSuggestionCommand(
                suggestion_id=suggestion_id,
                decision=parsed_decision,
                rationale=rationale,
                title=title,
                description=description,
                profession_slugs=profession_slugs,
                category_slugs=category_slugs,
            ),
        )
    except DomainError as exc:
        status_code = 400 if exc.code is ErrorCode.VALIDATION_ERROR else 403
        if exc.code is ErrorCode.NOT_FOUND:
            status_code = 404
        if exc.code is ErrorCode.CONFLICT:
            status_code = 409

        suggestion = None
        decisions = []
        try:
            result = await review_query_handler.handle(
                actor=user,
                query=GetSuggestionForReviewQuery(suggestion_id=suggestion_id),
            )
            suggestion = result.suggestion
            decisions = result.decisions
        except DomainError:
            pass

        return templates.TemplateResponse(
            request=request,
            name="suggestions_review_detail.html",
            context={
                "request": request,
                "user": user,
                "csrf_token": csrf_token,
                "saved": None,
                "error": exc.message,
                "suggestion": suggestion,
                "decisions": decisions,
                "professions": professions,
                "categories": categories,
                "form": {
                    "title": title or "",
                    "description": description or "",
                    "profession_slugs": profession_slugs or [],
                    "category_slugs": category_slugs or [],
                    "rationale": rationale,
                    "decision": decision,
                },
                "can_decide": bool(
                    suggestion and suggestion.status == SuggestionStatus.PENDING_REVIEW
                ),
            },
            status_code=status_code,
        )

    return RedirectResponse(url=f"/admin/suggestions/{suggestion_id}?saved=1", status_code=303)
