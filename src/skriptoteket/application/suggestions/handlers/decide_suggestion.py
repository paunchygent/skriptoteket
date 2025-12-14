from __future__ import annotations

from skriptoteket.application.suggestions.commands import (
    DecideSuggestionCommand,
    DecideSuggestionResult,
)
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.suggestions.models import (
    SuggestionDecisionType,
    decide_suggestion,
)
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.suggestions import (
    DecideSuggestionHandlerProtocol,
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class DecideSuggestionHandler(DecideSuggestionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        suggestions: SuggestionRepositoryProtocol,
        decisions: SuggestionDecisionRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._suggestions = suggestions
        self._decisions = decisions
        self._tools = tools
        self._professions = professions
        self._categories = categories
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: DecideSuggestionCommand,
    ) -> DecideSuggestionResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        decision_id = self._id_generator.new_uuid()
        draft_tool_id = (
            self._id_generator.new_uuid()
            if command.decision is SuggestionDecisionType.ACCEPT
            else None
        )

        async with self._uow:
            suggestion = await self._suggestions.get_by_id(suggestion_id=command.suggestion_id)
            if suggestion is None:
                raise not_found("Suggestion", str(command.suggestion_id))

            updated_suggestion, decision_record = decide_suggestion(
                suggestion=suggestion,
                decision_id=decision_id,
                decided_by_user_id=actor.id,
                decision=command.decision,
                rationale=command.rationale,
                title=command.title,
                description=command.description,
                profession_slugs=command.profession_slugs,
                category_slugs=command.category_slugs,
                created_tool_id=draft_tool_id,
                now=now,
            )

            if decision_record.decision is SuggestionDecisionType.ACCEPT:
                profession_ids = []
                for slug in decision_record.profession_slugs:
                    profession = await self._professions.get_by_slug(slug)
                    if profession is None:
                        raise validation_error("Unknown profession", details={"slug": slug})
                    profession_ids.append(profession.id)

                category_ids = []
                for slug in decision_record.category_slugs:
                    category = await self._categories.get_by_slug(slug)
                    if category is None:
                        raise validation_error("Unknown category", details={"slug": slug})
                    category_ids.append(category.id)

                if decision_record.created_tool_id is None:
                    raise validation_error("Accepted suggestions must create a draft tool")

                tool = Tool(
                    id=decision_record.created_tool_id,
                    slug=f"draft-{suggestion.id}",
                    title=decision_record.title,
                    summary=decision_record.description,
                    created_at=now,
                    updated_at=now,
                )
                await self._tools.create_draft(
                    tool=tool,
                    profession_ids=profession_ids,
                    category_ids=category_ids,
                )

            await self._suggestions.update(suggestion=updated_suggestion)
            await self._decisions.create(decision=decision_record)

        return DecideSuggestionResult(
            suggestion_id=command.suggestion_id,
            decision_id=decision_id,
            draft_tool_id=draft_tool_id,
        )
