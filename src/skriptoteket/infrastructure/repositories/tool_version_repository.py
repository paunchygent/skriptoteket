from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol


class PostgreSQLToolVersionRepository(ToolVersionRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, version_id: UUID) -> ToolVersion | None:
        stmt = select(ToolVersionModel).where(ToolVersionModel.id == version_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolVersion.model_validate(model) if model else None

    async def get_active_for_tool(self, *, tool_id: UUID) -> ToolVersion | None:
        stmt = select(ToolVersionModel).where(
            ToolVersionModel.tool_id == tool_id,
            ToolVersionModel.state == VersionState.ACTIVE,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolVersion.model_validate(model) if model else None

    async def get_latest_for_tool(self, *, tool_id: UUID) -> ToolVersion | None:
        stmt = (
            select(ToolVersionModel)
            .where(ToolVersionModel.tool_id == tool_id)
            .order_by(ToolVersionModel.version_number.desc(), ToolVersionModel.id.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolVersion.model_validate(model) if model else None

    async def list_for_tool(
        self,
        *,
        tool_id: UUID,
        states: set[VersionState] | None = None,
        limit: int = 50,
    ) -> list[ToolVersion]:
        stmt = select(ToolVersionModel).where(ToolVersionModel.tool_id == tool_id)
        if states is not None:
            stmt = stmt.where(ToolVersionModel.state.in_(list(states)))

        stmt = stmt.order_by(
            ToolVersionModel.version_number.desc(), ToolVersionModel.id.desc()
        ).limit(limit)
        result = await self._session.execute(stmt)
        return [ToolVersion.model_validate(model) for model in result.scalars().all()]

    async def get_next_version_number(self, *, tool_id: UUID) -> int:
        stmt = select(func.max(ToolVersionModel.version_number)).where(
            ToolVersionModel.tool_id == tool_id
        )
        result = await self._session.execute(stmt)
        max_version = result.scalar_one()
        return int(max_version) + 1 if max_version is not None else 1

    async def create(self, *, version: ToolVersion) -> ToolVersion:
        model = ToolVersionModel(
            id=version.id,
            tool_id=version.tool_id,
            version_number=version.version_number,
            state=version.state,
            source_code=version.source_code,
            entrypoint=version.entrypoint,
            content_hash=version.content_hash,
            derived_from_version_id=version.derived_from_version_id,
            created_by_user_id=version.created_by_user_id,
            created_at=version.created_at,
            submitted_for_review_by_user_id=version.submitted_for_review_by_user_id,
            submitted_for_review_at=version.submitted_for_review_at,
            reviewed_by_user_id=version.reviewed_by_user_id,
            reviewed_at=version.reviewed_at,
            published_by_user_id=version.published_by_user_id,
            published_at=version.published_at,
            change_summary=version.change_summary,
            review_note=version.review_note,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ToolVersion.model_validate(model)

    async def update(self, *, version: ToolVersion) -> ToolVersion:
        model = await self._session.get(ToolVersionModel, version.id)
        if model is None:
            return version

        model.state = version.state
        model.submitted_for_review_by_user_id = version.submitted_for_review_by_user_id
        model.submitted_for_review_at = version.submitted_for_review_at
        model.reviewed_by_user_id = version.reviewed_by_user_id
        model.reviewed_at = version.reviewed_at
        model.published_by_user_id = version.published_by_user_id
        model.published_at = version.published_at
        model.change_summary = version.change_summary
        model.review_note = version.review_note

        await self._session.flush()
        await self._session.refresh(model)
        return ToolVersion.model_validate(model)
