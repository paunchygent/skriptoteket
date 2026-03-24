"""PostgreSQL repository for classroom-planner seating export jobs.

Purpose:
    Map the dedicated seating export-job table to typed application models so
    async export orchestration can stay within the classroom-planner bounded
    context and UoW transaction flow.

Relationships:
    - Implements `SeatingExportJobRepositoryProtocol`.
    - Uses `SeatingExportJobModel` from the infrastructure DB model package.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportJob,
    SeatingExportJobStatus,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.models import (
    SeatingExportKind,
    SeatingExportLayoutId,
)
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_job import (
    SeatingExportJobModel,
)
from skriptoteket.protocols.classroom_planner_exports import SeatingExportJobRepositoryProtocol


class PostgreSQLSeatingExportJobRepository(SeatingExportJobRepositoryProtocol):
    """Persist dedicated seating export jobs in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(self, job: SeatingExportJob) -> SeatingExportJobModel:
        return SeatingExportJobModel(
            id=job.id,
            owner_user_id=job.owner_user_id,
            draft_id=job.draft_id,
            roster_id=job.roster_id,
            template_id=job.template_id,
            export_kind=job.export_kind.value,
            layout_id=job.layout_id.value,
            paper_size=job.paper_size.value,
            output_filename=job.output_filename,
            status=job.status.value,
            upstream_job_id=job.upstream_job_id,
            webhook_subscription_id=job.webhook_subscription_id,
            webhook_secret=job.webhook_secret,
            vault_file_id=job.vault_file_id,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _to_job(self, model: SeatingExportJobModel) -> SeatingExportJob:
        return SeatingExportJob(
            id=model.id,
            owner_user_id=model.owner_user_id,
            draft_id=model.draft_id,
            roster_id=model.roster_id,
            template_id=model.template_id,
            export_kind=SeatingExportKind(model.export_kind),
            layout_id=SeatingExportLayoutId(model.layout_id),
            paper_size=SeatingExportPaperSize(model.paper_size),
            output_filename=model.output_filename,
            status=SeatingExportJobStatus(model.status),
            upstream_job_id=model.upstream_job_id,
            webhook_subscription_id=model.webhook_subscription_id,
            webhook_secret=model.webhook_secret,
            vault_file_id=model.vault_file_id,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, *, job: SeatingExportJob) -> SeatingExportJob:
        model = self._to_model(job)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)

    async def get_by_id(self, *, job_id: UUID) -> SeatingExportJob | None:
        model = await self._session.get(SeatingExportJobModel, job_id)
        return self._to_job(model) if model else None

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> SeatingExportJob | None:
        result = await self._session.execute(
            select(SeatingExportJobModel).where(
                SeatingExportJobModel.upstream_job_id == upstream_job_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_job(model) if model else None

    async def update(self, *, job: SeatingExportJob) -> SeatingExportJob:
        model = await self._session.get(SeatingExportJobModel, job.id)
        if model is None:
            return job

        model.status = job.status.value
        model.upstream_job_id = job.upstream_job_id
        model.webhook_subscription_id = job.webhook_subscription_id
        model.webhook_secret = job.webhook_secret
        model.vault_file_id = job.vault_file_id
        model.error_message = job.error_message
        model.paper_size = job.paper_size.value
        model.output_filename = job.output_filename
        model.layout_id = job.layout_id.value
        model.export_kind = job.export_kind.value
        model.roster_id = job.roster_id
        model.template_id = job.template_id

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)
