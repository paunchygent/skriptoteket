from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import ToolVersionStats
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol


class PostgreSQLToolVersionRepository(ToolVersionRepositoryProtocol):
    """PostgreSQL repository for tool versions.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

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

    async def get_version_stats_for_tools(
        self, *, tool_ids: list[UUID]
    ) -> dict[UUID, ToolVersionStats]:
        """Get version statistics for multiple tools in one batch query (ADR-0033).

        Uses indexed columns (tool_id, state) for efficient aggregation.
        """
        if not tool_ids:
            return {}

        # Query 1: Aggregate counts and IN_REVIEW status per tool
        agg_stmt = (
            select(
                ToolVersionModel.tool_id,
                func.count(ToolVersionModel.id).label("version_count"),
                func.max(
                    case(
                        (ToolVersionModel.state == VersionState.IN_REVIEW, 1),
                        else_=0,
                    )
                ).label("has_in_review"),
            )
            .where(ToolVersionModel.tool_id.in_(tool_ids))
            .group_by(ToolVersionModel.tool_id)
        )
        agg_result = await self._session.execute(agg_stmt)
        agg_rows = {row.tool_id: row for row in agg_result.all()}

        # Query 2: Get latest version state per tool (highest version_number)
        # Using a subquery to get max version_number per tool
        max_version_subq = (
            select(
                ToolVersionModel.tool_id,
                func.max(ToolVersionModel.version_number).label("max_version"),
            )
            .where(ToolVersionModel.tool_id.in_(tool_ids))
            .group_by(ToolVersionModel.tool_id)
            .subquery()
        )

        latest_stmt = select(
            ToolVersionModel.tool_id,
            ToolVersionModel.state,
        ).join(
            max_version_subq,
            (ToolVersionModel.tool_id == max_version_subq.c.tool_id)
            & (ToolVersionModel.version_number == max_version_subq.c.max_version),
        )
        latest_result = await self._session.execute(latest_stmt)
        latest_by_tool = {row.tool_id: row.state for row in latest_result.all()}

        # Build result dict
        stats: dict[UUID, ToolVersionStats] = {}
        for tool_id in tool_ids:
            agg_row = agg_rows.get(tool_id)
            if agg_row:
                latest_state = latest_by_tool.get(tool_id)
                # latest_state is already a string from the raw query, not VersionState enum
                stats[tool_id] = ToolVersionStats(
                    version_count=agg_row.version_count,
                    latest_version_state=latest_state if latest_state else None,
                    has_pending_review=agg_row.has_in_review == 1,
                )
            else:
                # No versions for this tool
                stats[tool_id] = ToolVersionStats(
                    version_count=0,
                    latest_version_state=None,
                    has_pending_review=False,
                )

        return stats

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
            raise not_found("ToolVersion", str(version.id))

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
