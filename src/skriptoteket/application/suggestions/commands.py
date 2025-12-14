from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.suggestions.models import SuggestionDecisionType


class SubmitSuggestionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    profession_slugs: list[str]
    category_slugs: list[str]


class SubmitSuggestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID


class DecideSuggestionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID
    decision: SuggestionDecisionType
    rationale: str

    title: str | None = None
    description: str | None = None
    profession_slugs: list[str] | None = None
    category_slugs: list[str] | None = None


class DecideSuggestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID
    decision_id: UUID
    draft_tool_id: UUID | None = None
