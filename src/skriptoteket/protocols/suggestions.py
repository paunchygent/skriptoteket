from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.suggestions.commands import (
    DecideSuggestionCommand,
    DecideSuggestionResult,
    SubmitSuggestionCommand,
    SubmitSuggestionResult,
)
from skriptoteket.application.suggestions.queries import (
    GetSuggestionForReviewQuery,
    GetSuggestionForReviewResult,
    ListSuggestionsForReviewQuery,
    ListSuggestionsForReviewResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.suggestions.models import Suggestion, SuggestionDecision


class SuggestionRepositoryProtocol(Protocol):
    async def create(self, *, suggestion: Suggestion) -> Suggestion: ...

    async def get_by_id(self, *, suggestion_id: UUID) -> Suggestion | None: ...

    async def list_for_review(self) -> list[Suggestion]: ...

    async def update(self, *, suggestion: Suggestion) -> Suggestion: ...


class SuggestionDecisionRepositoryProtocol(Protocol):
    async def create(self, *, decision: SuggestionDecision) -> SuggestionDecision: ...

    async def list_for_suggestion(self, *, suggestion_id: UUID) -> list[SuggestionDecision]: ...


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


class GetSuggestionForReviewHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: GetSuggestionForReviewQuery,
    ) -> GetSuggestionForReviewResult: ...


class DecideSuggestionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: DecideSuggestionCommand,
    ) -> DecideSuggestionResult: ...
