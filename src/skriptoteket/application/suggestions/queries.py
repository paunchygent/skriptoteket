from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.suggestions.models import Suggestion


class ListSuggestionsForReviewQuery(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListSuggestionsForReviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestions: list[Suggestion]
