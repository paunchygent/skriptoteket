from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubmitSuggestionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    profession_slugs: list[str]
    category_slugs: list[str]


class SubmitSuggestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion_id: UUID
