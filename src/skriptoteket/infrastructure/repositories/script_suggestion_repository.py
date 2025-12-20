from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.suggestions.models import Suggestion
from skriptoteket.infrastructure.db.models.script_suggestion import ScriptSuggestionModel
from skriptoteket.protocols.suggestions import SuggestionRepositoryProtocol


class PostgreSQLScriptSuggestionRepository(SuggestionRepositoryProtocol):
    """PostgreSQL repository for script suggestions.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, suggestion: Suggestion) -> Suggestion:
        model = ScriptSuggestionModel(
            id=suggestion.id,
            submitted_by_user_id=suggestion.submitted_by_user_id,
            title=suggestion.title,
            description=suggestion.description,
            profession_slugs=list(suggestion.profession_slugs),
            category_slugs=list(suggestion.category_slugs),
            status=suggestion.status,
            reviewed_by_user_id=suggestion.reviewed_by_user_id,
            reviewed_at=suggestion.reviewed_at,
            review_rationale=suggestion.review_rationale,
            draft_tool_id=suggestion.draft_tool_id,
            created_at=suggestion.created_at,
            updated_at=suggestion.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return Suggestion.model_validate(model)

    async def get_by_id(self, *, suggestion_id: UUID) -> Suggestion | None:
        stmt = select(ScriptSuggestionModel).where(ScriptSuggestionModel.id == suggestion_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return Suggestion.model_validate(model) if model else None

    async def list_for_review(self) -> list[Suggestion]:
        stmt = select(ScriptSuggestionModel).order_by(
            ScriptSuggestionModel.created_at.desc(),
            ScriptSuggestionModel.id.desc(),
        )
        result = await self._session.execute(stmt)
        return [Suggestion.model_validate(model) for model in result.scalars().all()]

    async def update(self, *, suggestion: Suggestion) -> Suggestion:
        model = await self._session.get(ScriptSuggestionModel, suggestion.id)
        if model is None:
            raise not_found("Suggestion", str(suggestion.id))

        model.status = suggestion.status
        model.reviewed_by_user_id = suggestion.reviewed_by_user_id
        model.reviewed_at = suggestion.reviewed_at
        model.review_rationale = suggestion.review_rationale
        model.draft_tool_id = suggestion.draft_tool_id
        model.updated_at = suggestion.updated_at

        await self._session.flush()
        await self._session.refresh(model)
        return Suggestion.model_validate(model)
