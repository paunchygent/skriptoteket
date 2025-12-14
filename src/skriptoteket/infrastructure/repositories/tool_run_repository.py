from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.scripting.models import ToolRun
from skriptoteket.infrastructure.db.models.tool_run import ToolRunModel
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol


class PostgreSQLToolRunRepository(ToolRunRepositoryProtocol):
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
            context=run.context,
            requested_by_user_id=run.requested_by_user_id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            workdir_path=run.workdir_path,
            input_filename=run.input_filename,
            input_size_bytes=run.input_size_bytes,
            html_output=run.html_output,
            stdout=run.stdout,
            stderr=run.stderr,
            artifacts_manifest=run.artifacts_manifest,
            error_summary=run.error_summary,
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

        await self._session.flush()
        await self._session.refresh(model)
        return ToolRun.model_validate(model)
