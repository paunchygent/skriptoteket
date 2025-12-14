from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.suggestions.models import Suggestion
from skriptoteket.infrastructure.db.models.script_suggestion import ScriptSuggestionModel
from skriptoteket.protocols.suggestions import SuggestionRepositoryProtocol


class PostgreSQLScriptSuggestionRepository(SuggestionRepositoryProtocol):
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
            created_at=suggestion.created_at,
            updated_at=suggestion.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return Suggestion.model_validate(model)

    async def list_for_review(self) -> list[Suggestion]:
        stmt = select(ScriptSuggestionModel).order_by(
            ScriptSuggestionModel.created_at.desc(),
            ScriptSuggestionModel.id.desc(),
        )
        result = await self._session.execute(stmt)
        return [Suggestion.model_validate(model) for model in result.scalars().all()]
