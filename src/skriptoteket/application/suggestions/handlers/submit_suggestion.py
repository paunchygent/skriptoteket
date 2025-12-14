from __future__ import annotations

from skriptoteket.application.suggestions.commands import (
    SubmitSuggestionCommand,
    SubmitSuggestionResult,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.suggestions.models import create_suggestion
from skriptoteket.protocols.catalog import CategoryRepositoryProtocol, ProfessionRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.suggestions import (
    SubmitSuggestionHandlerProtocol,
    SuggestionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SubmitSuggestionHandler(SubmitSuggestionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        suggestions: SuggestionRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._suggestions = suggestions
        self._professions = professions
        self._categories = categories
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, command: SubmitSuggestionCommand
    ) -> SubmitSuggestionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        async with self._uow:
            for slug in command.profession_slugs:
                if await self._professions.get_by_slug(slug) is None:
                    raise validation_error("Unknown profession", details={"slug": slug})

            for slug in command.category_slugs:
                if await self._categories.get_by_slug(slug) is None:
                    raise validation_error("Unknown category", details={"slug": slug})

            suggestion = create_suggestion(
                suggestion_id=self._id_generator.new_uuid(),
                submitted_by_user_id=actor.id,
                title=command.title,
                description=command.description,
                profession_slugs=command.profession_slugs,
                category_slugs=command.category_slugs,
                now=self._clock.now(),
            )

            await self._suggestions.create(suggestion=suggestion)

        return SubmitSuggestionResult(suggestion_id=suggestion.id)
