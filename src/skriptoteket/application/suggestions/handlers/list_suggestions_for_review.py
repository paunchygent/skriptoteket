from __future__ import annotations

from skriptoteket.application.suggestions.queries import (
    ListSuggestionsForReviewQuery,
    ListSuggestionsForReviewResult,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.suggestions import (
    ListSuggestionsForReviewHandlerProtocol,
    SuggestionRepositoryProtocol,
)


class ListSuggestionsForReviewHandler(ListSuggestionsForReviewHandlerProtocol):
    def __init__(self, *, suggestions: SuggestionRepositoryProtocol) -> None:
        self._suggestions = suggestions

    async def handle(
        self, *, actor: User, query: ListSuggestionsForReviewQuery
    ) -> ListSuggestionsForReviewResult:
        del query  # no filters yet
        require_at_least_role(user=actor, role=Role.ADMIN)
        return ListSuggestionsForReviewResult(suggestions=await self._suggestions.list_for_review())
