from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.suggestions.models import SuggestionDecision
from skriptoteket.infrastructure.db.models.script_suggestion_decision import (
    ScriptSuggestionDecisionModel,
)
from skriptoteket.protocols.suggestions import SuggestionDecisionRepositoryProtocol


class PostgreSQLScriptSuggestionDecisionRepository(SuggestionDecisionRepositoryProtocol):
    """PostgreSQL repository for script suggestion review decisions.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, decision: SuggestionDecision) -> SuggestionDecision:
        model = ScriptSuggestionDecisionModel(
            id=decision.id,
            suggestion_id=decision.suggestion_id,
            decided_by_user_id=decision.decided_by_user_id,
            decision=decision.decision,
            rationale=decision.rationale,
            title=decision.title,
            description=decision.description,
            profession_slugs=list(decision.profession_slugs),
            category_slugs=list(decision.category_slugs),
            created_tool_id=decision.created_tool_id,
            decided_at=decision.decided_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return SuggestionDecision.model_validate(model)

    async def list_for_suggestion(self, *, suggestion_id: UUID) -> list[SuggestionDecision]:
        stmt = (
            select(ScriptSuggestionDecisionModel)
            .where(ScriptSuggestionDecisionModel.suggestion_id == suggestion_id)
            .order_by(
                ScriptSuggestionDecisionModel.decided_at.desc(),
                ScriptSuggestionDecisionModel.id.desc(),
            )
        )
        result = await self._session.execute(stmt)
        return [SuggestionDecision.model_validate(model) for model in result.scalars().all()]
