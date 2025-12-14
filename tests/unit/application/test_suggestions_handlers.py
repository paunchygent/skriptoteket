from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.suggestions.commands import SubmitSuggestionCommand
from skriptoteket.application.suggestions.handlers.list_suggestions_for_review import (
    ListSuggestionsForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.submit_suggestion import SubmitSuggestionHandler
from skriptoteket.application.suggestions.queries import ListSuggestionsForReviewQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.suggestions.models import create_suggestion
from skriptoteket.protocols.catalog import CategoryRepositoryProtocol, ProfessionRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.suggestions import SuggestionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.catalog_fixtures import make_category, make_profession
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_suggestion_requires_contributor(now: datetime) -> None:
    uow = FakeUow()
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = SubmitSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    actor = make_user(role=Role.USER)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=SubmitSuggestionCommand(
                title="My idea",
                description="A useful script",
                profession_slugs=["larare"],
                category_slugs=["lektionsplanering"],
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    suggestions.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_suggestion_rejects_unknown_profession(now: datetime) -> None:
    uow = FakeUow()
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    professions.get_by_slug.return_value = None
    categories.get_by_slug.return_value = make_category(now=now)

    handler = SubmitSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    actor = make_user(role=Role.CONTRIBUTOR)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=SubmitSuggestionCommand(
                title="My idea",
                description="A useful script",
                profession_slugs=["unknown"],
                category_slugs=["lektionsplanering"],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert uow.entered is True
    assert uow.exited is True
    suggestions.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_suggestion_rejects_unknown_category(now: datetime) -> None:
    uow = FakeUow()
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    professions.get_by_slug.return_value = make_profession(now=now)
    categories.get_by_slug.return_value = None

    handler = SubmitSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    actor = make_user(role=Role.CONTRIBUTOR)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=SubmitSuggestionCommand(
                title="My idea",
                description="A useful script",
                profession_slugs=["larare"],
                category_slugs=["unknown"],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert uow.entered is True
    assert uow.exited is True
    suggestions.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_suggestion_persists_suggestion(now: datetime) -> None:
    uow = FakeUow()
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    suggestion_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=suggestion_id))

    professions.get_by_slug.return_value = make_profession(now=now)
    categories.get_by_slug.return_value = make_category(now=now)

    suggestions.create.return_value = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=uuid4(),
        title="My idea",
        description="A useful script",
        profession_slugs=["larare"],
        category_slugs=["lektionsplanering"],
        now=now,
    )

    handler = SubmitSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    actor = make_user(role=Role.CONTRIBUTOR)
    result = await handler.handle(
        actor=actor,
        command=SubmitSuggestionCommand(
            title="My idea",
            description="A useful script",
            profession_slugs=["larare"],
            category_slugs=["lektionsplanering"],
        ),
    )

    assert result.suggestion_id == suggestion_id
    assert uow.entered is True
    assert uow.exited is True

    suggestions.create.assert_awaited_once()
    created = suggestions.create.await_args.kwargs["suggestion"]
    assert created.submitted_by_user_id == actor.id
    assert created.profession_slugs == ("larare",)
    assert created.category_slugs == ("lektionsplanering",)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_suggestions_for_review_requires_admin(now: datetime) -> None:
    del now  # not needed
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    handler = ListSuggestionsForReviewHandler(suggestions=suggestions)

    actor = make_user(role=Role.CONTRIBUTOR)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=ListSuggestionsForReviewQuery())

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    suggestions.list_for_review.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_suggestions_for_review_returns_suggestions(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    suggestions_repo = AsyncMock(spec=SuggestionRepositoryProtocol)

    suggestion = create_suggestion(
        suggestion_id=uuid4(),
        submitted_by_user_id=actor.id,
        title="Idea",
        description="Desc",
        profession_slugs=["larare"],
        category_slugs=["lektionsplanering"],
        now=now,
    )
    suggestions_repo.list_for_review.return_value = [suggestion]

    handler = ListSuggestionsForReviewHandler(suggestions=suggestions_repo)
    result = await handler.handle(actor=actor, query=ListSuggestionsForReviewQuery())

    assert result.suggestions == [suggestion]
    suggestions_repo.list_for_review.assert_awaited_once()
