from __future__ import annotations

from typing import Protocol

from skriptoteket.application.suggestions.commands import (
    SubmitSuggestionCommand,
    SubmitSuggestionResult,
)
from skriptoteket.application.suggestions.queries import (
    ListSuggestionsForReviewQuery,
    ListSuggestionsForReviewResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.suggestions.models import Suggestion


class SuggestionRepositoryProtocol(Protocol):
    async def create(self, *, suggestion: Suggestion) -> Suggestion: ...

    async def list_for_review(self) -> list[Suggestion]: ...


class SubmitSuggestionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: SubmitSuggestionCommand,
    ) -> SubmitSuggestionResult: ...


class ListSuggestionsForReviewHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListSuggestionsForReviewQuery,
    ) -> ListSuggestionsForReviewResult: ...
