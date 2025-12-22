"""Suggestions API endpoints for SPA contributor/admin flows (ST-11-10)."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, status

from skriptoteket.application.suggestions.commands import (
    DecideSuggestionCommand,
    SubmitSuggestionCommand,
)
from skriptoteket.application.suggestions.queries import (
    GetSuggestionForReviewQuery,
    ListSuggestionsForReviewQuery,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.suggestions import (
    DecideSuggestionHandlerProtocol,
    GetSuggestionForReviewHandlerProtocol,
    ListSuggestionsForReviewHandlerProtocol,
    SubmitSuggestionHandlerProtocol,
)
from skriptoteket.web.api.v1.suggestions_dto import (
    DecideSuggestionRequest,
    DecideSuggestionResponse,
    ListSuggestionsResponse,
    SubmitSuggestionRequest,
    SubmitSuggestionResponse,
    SuggestionDetailResponse,
    to_decision,
    to_detail,
    to_summary,
)
from skriptoteket.web.auth.api_dependencies import (
    require_admin_api,
    require_contributor_api,
    require_csrf_token,
)

router = APIRouter(prefix="/api/v1", tags=["suggestions"])


@router.post(
    "/suggestions",
    response_model=SubmitSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def submit_suggestion(
    request: SubmitSuggestionRequest,
    handler: FromDishka[SubmitSuggestionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SubmitSuggestionResponse:
    result = await handler.handle(
        actor=user,
        command=SubmitSuggestionCommand(
            title=request.title,
            description=request.description,
            profession_slugs=request.profession_slugs,
            category_slugs=request.category_slugs,
        ),
    )
    return SubmitSuggestionResponse(suggestion_id=result.suggestion_id)


@router.get(
    "/admin/suggestions",
    response_model=ListSuggestionsResponse,
)
@inject
async def list_suggestions_for_review(
    handler: FromDishka[ListSuggestionsForReviewHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> ListSuggestionsResponse:
    result = await handler.handle(actor=user, query=ListSuggestionsForReviewQuery())
    return ListSuggestionsResponse(suggestions=[to_summary(s) for s in result.suggestions])


@router.get(
    "/admin/suggestions/{suggestion_id}",
    response_model=SuggestionDetailResponse,
)
@inject
async def get_suggestion_for_review(
    suggestion_id: UUID,
    handler: FromDishka[GetSuggestionForReviewHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> SuggestionDetailResponse:
    result = await handler.handle(
        actor=user,
        query=GetSuggestionForReviewQuery(suggestion_id=suggestion_id),
    )
    return SuggestionDetailResponse(
        suggestion=to_detail(result.suggestion),
        decisions=[to_decision(decision) for decision in result.decisions],
    )


@router.post(
    "/admin/suggestions/{suggestion_id}/decide",
    response_model=DecideSuggestionResponse,
)
@inject
async def decide_suggestion(
    suggestion_id: UUID,
    request: DecideSuggestionRequest,
    handler: FromDishka[DecideSuggestionHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> DecideSuggestionResponse:
    result = await handler.handle(
        actor=user,
        command=DecideSuggestionCommand(
            suggestion_id=suggestion_id,
            decision=request.decision,
            rationale=request.rationale,
            title=request.title,
            description=request.description,
            profession_slugs=request.profession_slugs,
            category_slugs=request.category_slugs,
        ),
    )
    return DecideSuggestionResponse(
        suggestion_id=result.suggestion_id,
        decision_id=result.decision_id,
        draft_tool_id=result.draft_tool_id,
    )
