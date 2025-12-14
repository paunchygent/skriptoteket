from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.suggestions.models import Suggestion, SuggestionDecision


class ListSuggestionsForReviewQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListSuggestionsForReviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestions: list[Suggestion]


class GetSuggestionForReviewQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID


class GetSuggestionForReviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion: Suggestion
    decisions: list[SuggestionDecision]
