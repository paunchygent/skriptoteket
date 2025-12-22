"""DTOs and mappers for suggestions API (keeps router slim)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.suggestions.models import (
    Suggestion,
    SuggestionDecision,
    SuggestionDecisionType,
    SuggestionStatus,
)


class SubmitSuggestionRequest(BaseModel):
    """Payload for creating a new suggestion (contributor+)."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    profession_slugs: list[str]
    category_slugs: list[str]


class SubmitSuggestionResponse(BaseModel):
    """Response after creating a suggestion."""

    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID


class SuggestionSummary(BaseModel):
    """Minimal suggestion representation for admin list."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    status: SuggestionStatus
    submitted_by_user_id: UUID
    created_at: datetime
    profession_slugs: tuple[str, ...]
    category_slugs: tuple[str, ...]


class ListSuggestionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestions: list[SuggestionSummary]


class SuggestionDetail(BaseModel):
    """Full suggestion detail for admin review."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    description: str
    status: SuggestionStatus
    submitted_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_rationale: str | None = None
    draft_tool_id: UUID | None = None
    profession_slugs: tuple[str, ...]
    category_slugs: tuple[str, ...]


class SuggestionDecisionItem(BaseModel):
    """Decision history entry for a suggestion."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    suggestion_id: UUID
    decided_by_user_id: UUID
    decision: SuggestionDecisionType
    rationale: str
    title: str
    description: str
    profession_slugs: tuple[str, ...]
    category_slugs: tuple[str, ...]
    created_tool_id: UUID | None = None
    decided_at: datetime


class SuggestionDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion: SuggestionDetail
    decisions: list[SuggestionDecisionItem]


class DecideSuggestionRequest(BaseModel):
    """Admin decision payload for a suggestion."""

    model_config = ConfigDict(frozen=True)

    decision: SuggestionDecisionType
    rationale: str
    title: str | None = None
    description: str | None = None
    profession_slugs: list[str] | None = None
    category_slugs: list[str] | None = None


class DecideSuggestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID
    decision_id: UUID
    draft_tool_id: UUID | None = None


def to_summary(suggestion: Suggestion) -> SuggestionSummary:
    return SuggestionSummary(
        id=suggestion.id,
        title=suggestion.title,
        status=suggestion.status,
        submitted_by_user_id=suggestion.submitted_by_user_id,
        created_at=suggestion.created_at,
        profession_slugs=tuple(suggestion.profession_slugs),
        category_slugs=tuple(suggestion.category_slugs),
    )


def to_detail(suggestion: Suggestion) -> SuggestionDetail:
    return SuggestionDetail(
        id=suggestion.id,
        title=suggestion.title,
        description=suggestion.description,
        status=suggestion.status,
        submitted_by_user_id=suggestion.submitted_by_user_id,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
        reviewed_by_user_id=suggestion.reviewed_by_user_id,
        reviewed_at=suggestion.reviewed_at,
        review_rationale=suggestion.review_rationale,
        draft_tool_id=suggestion.draft_tool_id,
        profession_slugs=tuple(suggestion.profession_slugs),
        category_slugs=tuple(suggestion.category_slugs),
    )


def to_decision(decision: SuggestionDecision) -> SuggestionDecisionItem:
    return SuggestionDecisionItem(
        id=decision.id,
        suggestion_id=decision.suggestion_id,
        decided_by_user_id=decision.decided_by_user_id,
        decision=decision.decision,
        rationale=decision.rationale,
        title=decision.title,
        description=decision.description,
        profession_slugs=tuple(decision.profession_slugs),
        category_slugs=tuple(decision.category_slugs),
        created_tool_id=decision.created_tool_id,
        decided_at=decision.decided_at,
    )
