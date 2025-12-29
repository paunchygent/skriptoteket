from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.scripting.models import RunContext, RunSourceKind, ToolRun
from skriptoteket.infrastructure.db.models.tool_run import ToolRunModel
from skriptoteket.protocols.scripting import RecentRunRow, ToolRunRepositoryProtocol


class PostgreSQLToolRunRepository(ToolRunRepositoryProtocol):
    """PostgreSQL repository for tool run records.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, run_id: UUID) -> ToolRun | None:
        stmt = select(ToolRunModel).where(ToolRunModel.id == run_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolRun.model_validate(model) if model else None

    async def create(self, *, run: ToolRun) -> ToolRun:
        model = ToolRunModel(
            id=run.id,
            tool_id=run.tool_id,
            version_id=run.version_id,
            snapshot_id=run.snapshot_id,
            source_kind=run.source_kind.value,
            curated_app_id=run.curated_app_id,
            curated_app_version=run.curated_app_version,
            context=run.context,
            requested_by_user_id=run.requested_by_user_id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            workdir_path=run.workdir_path,
            input_filename=run.input_filename,
            input_size_bytes=run.input_size_bytes,
            input_manifest=run.input_manifest.model_dump(),
            input_values=run.input_values,
            html_output=run.html_output,
            stdout=run.stdout,
            stderr=run.stderr,
            artifacts_manifest=run.artifacts_manifest,
            error_summary=run.error_summary,
            ui_payload=None if run.ui_payload is None else run.ui_payload.model_dump(),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ToolRun.model_validate(model)

    async def update(self, *, run: ToolRun) -> ToolRun:
        model = await self._session.get(ToolRunModel, run.id)
        if model is None:
            raise not_found("ToolRun", str(run.id))

        model.status = run.status
        model.finished_at = run.finished_at
        model.html_output = run.html_output
        model.stdout = run.stdout
        model.stderr = run.stderr
        model.artifacts_manifest = run.artifacts_manifest
        model.error_summary = run.error_summary
        model.ui_payload = None if run.ui_payload is None else run.ui_payload.model_dump()

        await self._session.flush()
        await self._session.refresh(model)
        return ToolRun.model_validate(model)

    async def get_latest_for_user_and_tool(
        self,
        *,
        user_id: UUID,
        tool_id: UUID,
        context: RunContext,
    ) -> ToolRun | None:
        stmt = (
            select(ToolRunModel)
            .where(ToolRunModel.requested_by_user_id == user_id)
            .where(ToolRunModel.tool_id == tool_id)
            .where(ToolRunModel.context == context.value)
            .order_by(ToolRunModel.started_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolRun.model_validate(model) if model else None

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        context: RunContext,
        limit: int = 50,
    ) -> list[ToolRun]:
        stmt = (
            select(ToolRunModel)
            .where(ToolRunModel.requested_by_user_id == user_id)
            .where(ToolRunModel.context == context.value)
            .order_by(ToolRunModel.started_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [ToolRun.model_validate(m) for m in models]

    async def count_for_user_this_month(
        self,
        *,
        user_id: UUID,
        context: RunContext,
    ) -> int:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count())
            .select_from(ToolRunModel)
            .where(ToolRunModel.requested_by_user_id == user_id)
            .where(ToolRunModel.context == context.value)
            .where(ToolRunModel.started_at >= month_start)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_recent_tools_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 10,
    ) -> list[RecentRunRow]:
        last_run = func.max(ToolRunModel.started_at)
        stmt = (
            select(
                ToolRunModel.source_kind,
                ToolRunModel.tool_id,
                ToolRunModel.curated_app_id,
                last_run.label("last_run"),
            )
            .where(ToolRunModel.requested_by_user_id == user_id)
            .where(ToolRunModel.context == RunContext.PRODUCTION.value)
            .where(
                ToolRunModel.source_kind.in_(
                    [
                        RunSourceKind.TOOL_VERSION.value,
                        RunSourceKind.CURATED_APP.value,
                    ]
                )
            )
            .group_by(
                ToolRunModel.source_kind,
                ToolRunModel.tool_id,
                ToolRunModel.curated_app_id,
            )
            .order_by(last_run.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            RecentRunRow(
                source_kind=RunSourceKind(row.source_kind),
                tool_id=row.tool_id,
                curated_app_id=row.curated_app_id,
                last_used_at=row.last_run,
            )
            for row in result.all()
        ]
