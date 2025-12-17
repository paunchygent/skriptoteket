"""Suggestions domain provider: script suggestion workflow handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.suggestions.handlers.decide_suggestion import DecideSuggestionHandler
from skriptoteket.application.suggestions.handlers.get_suggestion_for_review import (
    GetSuggestionForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.list_suggestions_for_review import (
    ListSuggestionsForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.submit_suggestion import SubmitSuggestionHandler
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.suggestions import (
    DecideSuggestionHandlerProtocol,
    GetSuggestionForReviewHandlerProtocol,
    ListSuggestionsForReviewHandlerProtocol,
    SubmitSuggestionHandlerProtocol,
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SuggestionsProvider(Provider):
    """Provides suggestion workflow handlers."""

    @provide(scope=Scope.REQUEST)
    def submit_suggestion_handler(
        self,
        uow: UnitOfWorkProtocol,
        suggestions: SuggestionRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SubmitSuggestionHandlerProtocol:
        return SubmitSuggestionHandler(
            uow=uow,
            suggestions=suggestions,
            professions=professions,
            categories=categories,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def list_suggestions_for_review_handler(
        self, suggestions: SuggestionRepositoryProtocol
    ) -> ListSuggestionsForReviewHandlerProtocol:
        return ListSuggestionsForReviewHandler(suggestions=suggestions)

    @provide(scope=Scope.REQUEST)
    def get_suggestion_for_review_handler(
        self,
        suggestions: SuggestionRepositoryProtocol,
        decisions: SuggestionDecisionRepositoryProtocol,
    ) -> GetSuggestionForReviewHandlerProtocol:
        return GetSuggestionForReviewHandler(suggestions=suggestions, decisions=decisions)

    @provide(scope=Scope.REQUEST)
    def decide_suggestion_handler(
        self,
        uow: UnitOfWorkProtocol,
        suggestions: SuggestionRepositoryProtocol,
        decisions: SuggestionDecisionRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> DecideSuggestionHandlerProtocol:
        return DecideSuggestionHandler(
            uow=uow,
            suggestions=suggestions,
            decisions=decisions,
            tools=tools,
            maintainers=maintainers,
            professions=professions,
            categories=categories,
            clock=clock,
            id_generator=id_generator,
        )
