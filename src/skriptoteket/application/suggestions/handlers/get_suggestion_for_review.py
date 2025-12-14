from __future__ import annotations

from skriptoteket.application.suggestions.queries import (
    GetSuggestionForReviewQuery,
    GetSuggestionForReviewResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.suggestions import (
    GetSuggestionForReviewHandlerProtocol,
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
)


class GetSuggestionForReviewHandler(GetSuggestionForReviewHandlerProtocol):
    def __init__(
        self,
        *,
        suggestions: SuggestionRepositoryProtocol,
        decisions: SuggestionDecisionRepositoryProtocol,
    ) -> None:
        self._suggestions = suggestions
        self._decisions = decisions

    async def handle(
        self,
        *,
        actor: User,
        query: GetSuggestionForReviewQuery,
    ) -> GetSuggestionForReviewResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        suggestion = await self._suggestions.get_by_id(suggestion_id=query.suggestion_id)
        if suggestion is None:
            raise not_found("Suggestion", str(query.suggestion_id))

        decisions = await self._decisions.list_for_suggestion(suggestion_id=query.suggestion_id)
        return GetSuggestionForReviewResult(suggestion=suggestion, decisions=decisions)
