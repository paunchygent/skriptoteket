from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import RedirectResponse

from skriptoteket.application.catalog.queries import (
    ListAllCategoriesResult,
    ListProfessionsResult,
)
from skriptoteket.application.suggestions.commands import (
    DecideSuggestionResult,
    SubmitSuggestionResult,
)
from skriptoteket.application.suggestions.queries import (
    GetSuggestionForReviewResult,
    ListSuggestionsForReviewResult,
)
from skriptoteket.domain.catalog.models import Category, Profession
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.domain.suggestions.models import (
    Suggestion,
    SuggestionDecision,
    SuggestionDecisionType,
    SuggestionStatus,
)
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
from skriptoteket.web.pages import suggestions


def _original(fn: Any) -> Any:
    return getattr(fn, "__dishka_orig_func__", fn)


def _request(*, path: str, method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: Role) -> User:
    now = _now()
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _session(*, user_id: uuid.UUID) -> Session:
    now = _now()
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )


def _profession(*, slug: str = "teacher") -> Profession:
    now = _now()
    return Profession(
        id=uuid.uuid4(),
        slug=slug,
        label=slug.title(),
        sort_order=1,
        created_at=now,
        updated_at=now,
    )


def _category(*, slug: str = "planning") -> Category:
    now = _now()
    return Category(
        id=uuid.uuid4(),
        slug=slug,
        label=slug.title(),
        created_at=now,
        updated_at=now,
    )


def _suggestion(*, status: SuggestionStatus) -> Suggestion:
    now = _now()
    return Suggestion(
        id=uuid.uuid4(),
        submitted_by_user_id=uuid.uuid4(),
        title="A script idea",
        description="Make this easier",
        profession_slugs=("teacher",),
        category_slugs=("planning",),
        status=status,
        reviewed_by_user_id=None,
        reviewed_at=None,
        review_rationale=None,
        draft_tool_id=None,
        created_at=now,
        updated_at=now,
    )


def _decision(*, suggestion_id: uuid.UUID) -> SuggestionDecision:
    now = _now()
    return SuggestionDecision(
        id=uuid.uuid4(),
        suggestion_id=suggestion_id,
        decided_by_user_id=uuid.uuid4(),
        decision=SuggestionDecisionType.ACCEPT,
        rationale="Ok",
        title="A script idea",
        description="Make this easier",
        profession_slugs=("teacher",),
        category_slugs=("planning",),
        created_tool_id=None,
        decided_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_new_suggestion_page_renders_form_with_taxonomy_lists() -> None:
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)

    professions = [_profession(slug="teacher")]
    categories = [_category(slug="planning")]
    professions_handler.handle.return_value = ListProfessionsResult(professions=professions)
    categories_handler.handle.return_value = ListAllCategoriesResult(categories=categories)

    user = _user(role=Role.CONTRIBUTOR)
    session = _session(user_id=user.id)
    request = _request(path="/suggestions/new")

    response = await _original(suggestions.new_suggestion_page)(
        request=request,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        user=user,
        session=session,
        submitted=None,
    )

    assert response.status_code == 200
    assert response.template.name == "suggestions_new.html"
    assert response.context["csrf_token"] == session.csrf_token
    assert response.context["error"] is None
    assert response.context["professions"] == professions
    assert response.context["categories"] == categories
    assert response.context["form"]["title"] == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_suggestion_success_redirects_and_normalizes_empty_lists() -> None:
    handler = AsyncMock(spec=SubmitSuggestionHandlerProtocol)
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)

    handler.handle.return_value = SubmitSuggestionResult(suggestion_id=uuid.uuid4())

    user = _user(role=Role.CONTRIBUTOR)
    request = _request(path="/suggestions/new", method="POST")

    response = await _original(suggestions.submit_suggestion)(
        request=request,
        handler=handler,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        title="Title",
        description="Desc",
        profession_slugs=None,
        category_slugs=None,
        user=user,
        session=None,
    )

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == "/suggestions/new?submitted=1"

    called_command = handler.handle.call_args.kwargs["command"]
    assert called_command.profession_slugs == []
    assert called_command.category_slugs == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_suggestion_validation_error_renders_template_with_status_400() -> None:
    handler = AsyncMock(spec=SubmitSuggestionHandlerProtocol)
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)

    handler.handle.side_effect = DomainError(code=ErrorCode.VALIDATION_ERROR, message="Bad input")
    professions = [_profession(slug="teacher")]
    categories = [_category(slug="planning")]
    professions_handler.handle.return_value = ListProfessionsResult(professions=professions)
    categories_handler.handle.return_value = ListAllCategoriesResult(categories=categories)

    user = _user(role=Role.CONTRIBUTOR)
    session = _session(user_id=user.id)
    request = _request(path="/suggestions/new", method="POST")

    response = await _original(suggestions.submit_suggestion)(
        request=request,
        handler=handler,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        title="Title",
        description="Desc",
        profession_slugs=["teacher"],
        category_slugs=["planning"],
        user=user,
        session=session,
    )

    assert response.status_code == 400
    assert response.template.name == "suggestions_new.html"
    assert response.context["error"] == "Bad input"
    assert response.context["submitted"] is None
    assert response.context["form"]["title"] == "Title"
    assert response.context["form"]["profession_slugs"] == ["teacher"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestions_review_queue_renders_queue_template() -> None:
    handler = AsyncMock(spec=ListSuggestionsForReviewHandlerProtocol)
    suggestion = _suggestion(status=SuggestionStatus.PENDING_REVIEW)
    handler.handle.return_value = ListSuggestionsForReviewResult(suggestions=[suggestion])

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path="/admin/suggestions")

    response = await _original(suggestions.suggestions_review_queue)(
        request=request,
        handler=handler,
        user=user,
        session=session,
    )

    assert response.status_code == 200
    assert response.template.name == "suggestions_review_queue.html"
    assert response.context["csrf_token"] == session.csrf_token
    assert response.context["suggestions"] == [suggestion]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestion_review_detail_success_sets_can_decide_for_pending() -> None:
    handler = AsyncMock(spec=GetSuggestionForReviewHandlerProtocol)
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)

    suggestion = _suggestion(status=SuggestionStatus.PENDING_REVIEW)
    decisions = [_decision(suggestion_id=suggestion.id)]
    handler.handle.return_value = GetSuggestionForReviewResult(
        suggestion=suggestion, decisions=decisions
    )
    professions = [_profession(slug="teacher")]
    categories = [_category(slug="planning")]
    professions_handler.handle.return_value = ListProfessionsResult(professions=professions)
    categories_handler.handle.return_value = ListAllCategoriesResult(categories=categories)

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)
    request = _request(path=f"/admin/suggestions/{suggestion.id}")

    response = await _original(suggestions.suggestion_review_detail)(
        request=request,
        suggestion_id=suggestion.id,
        handler=handler,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        user=user,
        session=session,
        saved="1",
    )

    assert response.status_code == 200
    assert response.template.name == "suggestions_review_detail.html"
    assert response.context["saved"] == "1"
    assert response.context["suggestion"] == suggestion
    assert response.context["decisions"] == decisions
    assert response.context["can_decide"] is True
    assert response.context["form"]["decision"] == "accept"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestion_review_detail_not_found_renders_template_with_404() -> None:
    handler = AsyncMock(spec=GetSuggestionForReviewHandlerProtocol)
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)

    handler.handle.side_effect = DomainError(code=ErrorCode.NOT_FOUND, message="Missing")
    professions_handler.handle.return_value = ListProfessionsResult(professions=[_profession()])
    categories_handler.handle.return_value = ListAllCategoriesResult(categories=[_category()])

    user = _user(role=Role.ADMIN)
    request = _request(path="/admin/suggestions/x")

    response = await _original(suggestions.suggestion_review_detail)(
        request=request,
        suggestion_id=uuid.uuid4(),
        handler=handler,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        user=user,
        session=None,
        saved=None,
    )

    assert response.status_code == 404
    assert response.template.name == "suggestions_review_detail.html"
    assert response.context["suggestion"] is None
    assert response.context["can_decide"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decide_suggestion_invalid_decision_defaults_to_deny_and_redirects() -> None:
    handler = AsyncMock(spec=DecideSuggestionHandlerProtocol)
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)
    review_query_handler = AsyncMock(spec=GetSuggestionForReviewHandlerProtocol)

    suggestion_id = uuid.uuid4()
    handler.handle.return_value = DecideSuggestionResult(
        suggestion_id=suggestion_id, decision_id=uuid.uuid4()
    )
    professions_handler.handle.return_value = ListProfessionsResult(professions=[_profession()])
    categories_handler.handle.return_value = ListAllCategoriesResult(categories=[_category()])

    user = _user(role=Role.ADMIN)
    request = _request(path=f"/admin/suggestions/{suggestion_id}/decision", method="POST")

    response = await _original(suggestions.decide_suggestion)(
        request=request,
        suggestion_id=suggestion_id,
        handler=handler,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        review_query_handler=review_query_handler,
        decision="nonsense",
        rationale="No",
        title="Title",
        description="Desc",
        profession_slugs=["teacher"],
        category_slugs=["planning"],
        user=user,
        session=None,
    )

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/suggestions/{suggestion_id}?saved=1"

    called_command = handler.handle.call_args.kwargs["command"]
    assert called_command.decision is SuggestionDecisionType.DENY
    assert called_command.title is None
    assert called_command.profession_slugs is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decide_suggestion_domain_error_renders_detail_template_with_status() -> None:
    handler = AsyncMock(spec=DecideSuggestionHandlerProtocol)
    professions_handler = AsyncMock(spec=ListProfessionsHandlerProtocol)
    categories_handler = AsyncMock(spec=ListAllCategoriesHandlerProtocol)
    review_query_handler = AsyncMock(spec=GetSuggestionForReviewHandlerProtocol)

    suggestion = _suggestion(status=SuggestionStatus.PENDING_REVIEW)
    decisions = [_decision(suggestion_id=suggestion.id)]
    review_query_handler.handle.return_value = GetSuggestionForReviewResult(
        suggestion=suggestion,
        decisions=decisions,
    )
    handler.handle.side_effect = DomainError(code=ErrorCode.CONFLICT, message="Already reviewed")
    professions_handler.handle.return_value = ListProfessionsResult(professions=[_profession()])
    categories_handler.handle.return_value = ListAllCategoriesResult(categories=[_category()])

    user = _user(role=Role.ADMIN)
    request = _request(path=f"/admin/suggestions/{suggestion.id}/decision", method="POST")

    response = await _original(suggestions.decide_suggestion)(
        request=request,
        suggestion_id=suggestion.id,
        handler=handler,
        professions_handler=professions_handler,
        categories_handler=categories_handler,
        review_query_handler=review_query_handler,
        decision="accept",
        rationale="Because",
        title="Title",
        description="Desc",
        profession_slugs=["teacher"],
        category_slugs=["planning"],
        user=user,
        session=None,
    )

    assert response.status_code == 409
    assert response.template.name == "suggestions_review_detail.html"
    assert response.context["error"] == "Already reviewed"
    assert response.context["suggestion"] == suggestion
    assert response.context["decisions"] == decisions
    assert response.context["can_decide"] is True
