from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.suggestions.commands import (
    DecideSuggestionCommand,
    SubmitSuggestionCommand,
)
from skriptoteket.application.suggestions.handlers.decide_suggestion import DecideSuggestionHandler
from skriptoteket.application.suggestions.handlers.get_suggestion_for_review import (
    GetSuggestionForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.list_suggestions_for_review import (
    ListSuggestionsForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.submit_suggestion import SubmitSuggestionHandler
from skriptoteket.application.suggestions.queries import (
    GetSuggestionForReviewQuery,
    ListSuggestionsForReviewQuery,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.suggestions.models import (
    SuggestionDecision,
    SuggestionDecisionType,
    SuggestionStatus,
    create_suggestion,
)
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.suggestions import (
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
)
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_suggestion_for_review_requires_admin(now: datetime) -> None:
    del now  # not needed
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    decisions = AsyncMock(spec=SuggestionDecisionRepositoryProtocol)
    handler = GetSuggestionForReviewHandler(suggestions=suggestions, decisions=decisions)

    actor = make_user(role=Role.CONTRIBUTOR)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, query=GetSuggestionForReviewQuery(suggestion_id=uuid4()))

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    suggestions.get_by_id.assert_not_called()
    decisions.list_for_suggestion.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_suggestion_for_review_returns_suggestion_and_history(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    suggestion_id = uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=uuid4(),
        title="Idea",
        description="Desc",
        profession_slugs=["larare"],
        category_slugs=["lektionsplanering"],
        now=now,
    )

    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    suggestions.get_by_id.return_value = suggestion

    decisions = AsyncMock(spec=SuggestionDecisionRepositoryProtocol)
    decisions.list_for_suggestion.return_value = [
        SuggestionDecision(
            id=uuid4(),
            suggestion_id=suggestion_id,
            decided_by_user_id=actor.id,
            decision=SuggestionDecisionType.DENY,
            rationale="No",
            title=suggestion.title,
            description=suggestion.description,
            profession_slugs=suggestion.profession_slugs,
            category_slugs=suggestion.category_slugs,
            created_tool_id=None,
            decided_at=now,
        )
    ]

    handler = GetSuggestionForReviewHandler(suggestions=suggestions, decisions=decisions)
    result = await handler.handle(
        actor=actor, query=GetSuggestionForReviewQuery(suggestion_id=suggestion_id)
    )

    assert result.suggestion == suggestion
    assert len(result.decisions) == 1
    suggestions.get_by_id.assert_awaited_once_with(suggestion_id=suggestion_id)
    decisions.list_for_suggestion.assert_awaited_once_with(suggestion_id=suggestion_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decide_suggestion_requires_admin(now: datetime) -> None:
    uow = FakeUow()
    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    decisions = AsyncMock(spec=SuggestionDecisionRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = DecideSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        decisions=decisions,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    actor = make_user(role=Role.CONTRIBUTOR)
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=DecideSuggestionCommand(
                suggestion_id=uuid4(),
                decision=SuggestionDecisionType.DENY,
                rationale="No",
            ),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False
    suggestions.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decide_suggestion_accept_creates_draft_tool_and_records_decision(
    now: datetime,
) -> None:
    uow = FakeUow()
    actor = make_user(role=Role.ADMIN)
    suggestion_id = uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=uuid4(),
        title="Idea",
        description="Desc",
        profession_slugs=["larare"],
        category_slugs=["lektionsplanering"],
        now=now,
    )

    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    suggestions.get_by_id.return_value = suggestion

    decisions = AsyncMock(spec=SuggestionDecisionRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)

    profession = make_profession(now=now, slug="larare")
    category = make_category(now=now, slug="lektionsplanering")
    professions.get_by_slug.return_value = profession
    categories.get_by_slug.return_value = category

    decision_id = uuid4()
    tool_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(side_effect=[decision_id, tool_id]))
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = DecideSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        decisions=decisions,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=DecideSuggestionCommand(
            suggestion_id=suggestion_id,
            decision=SuggestionDecisionType.ACCEPT,
            rationale="Looks good",
            title="New title",
            description="New desc",
            profession_slugs=["larare"],
            category_slugs=["lektionsplanering"],
        ),
    )

    assert result.suggestion_id == suggestion_id
    assert result.decision_id == decision_id
    assert result.draft_tool_id == tool_id
    assert uow.entered is True
    assert uow.exited is True

    tools.create_draft.assert_awaited_once()
    tool_arg = tools.create_draft.await_args.kwargs["tool"]
    assert tool_arg.id == tool_id
    assert tool_arg.slug == f"draft-{suggestion_id}"
    assert tool_arg.title == "New title"

    suggestions.update.assert_awaited_once()
    updated = suggestions.update.await_args.kwargs["suggestion"]
    assert updated.status is SuggestionStatus.ACCEPTED
    assert updated.reviewed_by_user_id == actor.id
    assert updated.draft_tool_id == tool_id

    decisions.create.assert_awaited_once()
    decision = decisions.create.await_args.kwargs["decision"]
    assert decision.decision is SuggestionDecisionType.ACCEPT
    assert decision.created_tool_id == tool_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decide_suggestion_deny_does_not_create_tool(now: datetime) -> None:
    uow = FakeUow()
    actor = make_user(role=Role.ADMIN)
    suggestion_id = uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=uuid4(),
        title="Idea",
        description="Desc",
        profession_slugs=["larare"],
        category_slugs=["lektionsplanering"],
        now=now,
    )

    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    suggestions.get_by_id.return_value = suggestion

    decisions = AsyncMock(spec=SuggestionDecisionRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)

    decision_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=decision_id))
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = DecideSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        decisions=decisions,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=DecideSuggestionCommand(
            suggestion_id=suggestion_id,
            decision=SuggestionDecisionType.DENY,
            rationale="No",
        ),
    )

    assert result.suggestion_id == suggestion_id
    assert result.decision_id == decision_id
    assert result.draft_tool_id is None

    tools.create_draft.assert_not_called()
    suggestions.update.assert_awaited_once()
    updated = suggestions.update.await_args.kwargs["suggestion"]
    assert updated.status is SuggestionStatus.DENIED
    assert updated.draft_tool_id is None

    decisions.create.assert_awaited_once()
    decision = decisions.create.await_args.kwargs["decision"]
    assert decision.decision is SuggestionDecisionType.DENY
    assert decision.created_tool_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decide_suggestion_accept_rejects_unknown_profession(now: datetime) -> None:
    uow = FakeUow()
    actor = make_user(role=Role.ADMIN)
    suggestion_id = uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=uuid4(),
        title="Idea",
        description="Desc",
        profession_slugs=["larare"],
        category_slugs=["lektionsplanering"],
        now=now,
    )

    suggestions = AsyncMock(spec=SuggestionRepositoryProtocol)
    suggestions.get_by_id.return_value = suggestion

    decisions = AsyncMock(spec=SuggestionDecisionRepositoryProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    categories = AsyncMock(spec=CategoryRepositoryProtocol)

    professions.get_by_slug.return_value = None
    categories.get_by_slug.return_value = make_category(now=now, slug="lektionsplanering")

    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(side_effect=[uuid4(), uuid4()]))
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))

    handler = DecideSuggestionHandler(
        uow=uow,
        suggestions=suggestions,
        decisions=decisions,
        tools=tools,
        professions=professions,
        categories=categories,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=DecideSuggestionCommand(
                suggestion_id=suggestion_id,
                decision=SuggestionDecisionType.ACCEPT,
                rationale="Ok",
                title="New title",
                description="New desc",
                profession_slugs=["unknown"],
                category_slugs=["lektionsplanering"],
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    tools.create_draft.assert_not_called()
    suggestions.update.assert_not_called()
    decisions.create.assert_not_called()
