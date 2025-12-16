from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.application.suggestions.commands import (
    DecideSuggestionCommand,
)
from skriptoteket.application.suggestions.handlers.decide_suggestion import DecideSuggestionHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.suggestions.models import (
    Suggestion,
    SuggestionDecisionType,
    SuggestionStatus,
)


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


@pytest.fixture
def mock_suggestions():
    return AsyncMock()


@pytest.fixture
def mock_decisions():
    return AsyncMock()


@pytest.fixture
def mock_tools():
    return AsyncMock()


@pytest.fixture
def mock_professions():
    return AsyncMock()


@pytest.fixture
def mock_categories():
    return AsyncMock()


@pytest.fixture
def mock_clock():
    clock = MagicMock()
    clock.now.return_value = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return clock


@pytest.fixture
def mock_id_generator():
    gen = MagicMock()
    gen.new_uuid.side_effect = uuid4
    return gen


@pytest.fixture
def handler(
    mock_uow,
    mock_suggestions,
    mock_decisions,
    mock_tools,
    mock_professions,
    mock_categories,
    mock_clock,
    mock_id_generator,
):
    return DecideSuggestionHandler(
        uow=mock_uow,
        suggestions=mock_suggestions,
        decisions=mock_decisions,
        tools=mock_tools,
        professions=mock_professions,
        categories=mock_categories,
        clock=mock_clock,
        id_generator=mock_id_generator,
    )


def create_admin_user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        role=Role.ADMIN,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def create_pending_suggestion() -> Suggestion:
    return Suggestion(
        id=uuid4(),
        submitted_by_user_id=uuid4(),
        title="New Tool",
        description="A cool tool",
        profession_slugs=["prof1"],
        category_slugs=["cat1"],
        status=SuggestionStatus.PENDING_REVIEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_handle_accept_creates_draft_tool(
    handler, mock_suggestions, mock_professions, mock_categories, mock_tools, mock_decisions
):
    admin = create_admin_user()
    suggestion = create_pending_suggestion()

    mock_suggestions.get_by_id.return_value = suggestion

    # Mock profession/category lookup
    mock_professions.get_by_slug.return_value = MagicMock(id=uuid4())
    mock_categories.get_by_slug.return_value = MagicMock(id=uuid4())

    command = DecideSuggestionCommand(
        suggestion_id=suggestion.id,
        decision=SuggestionDecisionType.ACCEPT,
        rationale="Looks good",
        title="Accepted Tool",
        description="Official description",
        profession_slugs=["prof1"],
        category_slugs=["cat1"],
    )

    result = await handler.handle(actor=admin, command=command)

    # Assertions
    assert result.draft_tool_id is not None
    mock_suggestions.get_by_id.assert_called_with(suggestion_id=suggestion.id)
    mock_professions.get_by_slug.assert_called_with("prof1")
    mock_categories.get_by_slug.assert_called_with("cat1")

    # Verify tool creation
    mock_tools.create_draft.assert_called_once()
    created_tool = mock_tools.create_draft.call_args[1]["tool"]
    assert created_tool.title == "Accepted Tool"

    # Verify suggestion update
    mock_suggestions.update.assert_called_once()
    updated_suggestion = mock_suggestions.update.call_args[1]["suggestion"]
    assert updated_suggestion.status == SuggestionStatus.ACCEPTED

    # Verify decision recorded
    mock_decisions.create.assert_called_once()


@pytest.mark.asyncio
async def test_handle_reject_does_not_create_tool(
    handler, mock_suggestions, mock_tools, mock_decisions
):
    admin = create_admin_user()
    suggestion = create_pending_suggestion()
    mock_suggestions.get_by_id.return_value = suggestion

    command = DecideSuggestionCommand(
        suggestion_id=suggestion.id,
        decision=SuggestionDecisionType.DENY,
        rationale="Not relevant",
        title="Ignored",
        description="Ignored",
        profession_slugs=None,
        category_slugs=None,
    )

    result = await handler.handle(actor=admin, command=command)

    assert result.draft_tool_id is None
    mock_tools.create_draft.assert_not_called()

    # Verify suggestion update
    mock_suggestions.update.assert_called_once()
    updated_suggestion = mock_suggestions.update.call_args[1]["suggestion"]
    assert updated_suggestion.status == SuggestionStatus.DENIED


@pytest.mark.asyncio
async def test_handle_unauthorized_if_not_admin(handler):
    user = create_admin_user()
    user = user.model_copy(update={"role": Role.USER})

    command = DecideSuggestionCommand(
        suggestion_id=uuid4(),
        decision=SuggestionDecisionType.ACCEPT,
        rationale="test",
        title="test",
        description="test",
        profession_slugs=[],
        category_slugs=[],
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=user, command=command)
    assert exc.value.code == ErrorCode.FORBIDDEN


@pytest.mark.asyncio
async def test_handle_not_found_if_suggestion_missing(handler, mock_suggestions):
    admin = create_admin_user()
    mock_suggestions.get_by_id.return_value = None

    command = DecideSuggestionCommand(
        suggestion_id=uuid4(),
        decision=SuggestionDecisionType.ACCEPT,
        rationale="test",
        title="test",
        description="test",
        profession_slugs=[],
        category_slugs=[],
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=admin, command=command)
    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_handle_accept_validates_taxonomy(handler, mock_suggestions, mock_professions):
    admin = create_admin_user()
    suggestion = create_pending_suggestion()
    mock_suggestions.get_by_id.return_value = suggestion

    # Mock profession missing
    mock_professions.get_by_slug.return_value = None

    command = DecideSuggestionCommand(
        suggestion_id=suggestion.id,
        decision=SuggestionDecisionType.ACCEPT,
        rationale="ok",
        title="Tool",
        description="Desc",
        profession_slugs=["unknown_prof"],
        category_slugs=[],
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=admin, command=command)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_handle_accept_validates_category_taxonomy(
    handler, mock_suggestions, mock_professions, mock_categories
):
    admin = create_admin_user()
    suggestion = create_pending_suggestion()
    mock_suggestions.get_by_id.return_value = suggestion

    # Profession exists
    mock_professions.get_by_slug.return_value = MagicMock(id=uuid4())
    # Category missing
    mock_categories.get_by_slug.return_value = None

    command = DecideSuggestionCommand(
        suggestion_id=suggestion.id,
        decision=SuggestionDecisionType.ACCEPT,
        rationale="ok",
        title="Tool",
        description="Desc",
        profession_slugs=["prof1"],
        category_slugs=["unknown_cat"],
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(actor=admin, command=command)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
