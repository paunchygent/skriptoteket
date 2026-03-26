"""PostgreSQL repository for classroom-planner grouping export jobs.

Purpose:
    Map the dedicated grouping export-job table to typed application models so
    grouping export orchestration can stay inside the classroom-planner bounded
    context and the Unit of Work transaction flow.

Relationships:
    - Implements `GroupingExportJobRepositoryProtocol`.
    - Uses `GroupingExportJobModel` from the infrastructure DB model package.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportJob,
    GroupingExportJobStatus,
    GroupingExportKind,
    GroupingExportPaperSize,
)
from skriptoteket.infrastructure.db.models.classroom_planner_grouping_export_job import (
    GroupingExportJobModel,
)
from skriptoteket.protocols.classroom_planner_exports import GroupingExportJobRepositoryProtocol


class PostgreSQLGroupingExportJobRepository(GroupingExportJobRepositoryProtocol):
    """Persist dedicated grouping export jobs in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(self, job: GroupingExportJob) -> GroupingExportJobModel:
        return GroupingExportJobModel(
            id=job.id,
            owner_user_id=job.owner_user_id,
            draft_id=job.draft_id,
            roster_id=job.roster_id,
            export_kind=job.export_kind.value,
            paper_size=job.paper_size.value if job.paper_size is not None else None,
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

    def _to_job(self, model: GroupingExportJobModel) -> GroupingExportJob:
        return GroupingExportJob(
            id=model.id,
            owner_user_id=model.owner_user_id,
            draft_id=model.draft_id,
            roster_id=model.roster_id,
            export_kind=GroupingExportKind(model.export_kind),
            paper_size=GroupingExportPaperSize(model.paper_size)
            if model.paper_size is not None
            else None,
            output_filename=model.output_filename,
            status=GroupingExportJobStatus(model.status),
            upstream_job_id=model.upstream_job_id,
            webhook_subscription_id=model.webhook_subscription_id,
            webhook_secret=model.webhook_secret,
            vault_file_id=model.vault_file_id,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, *, job: GroupingExportJob) -> GroupingExportJob:
        model = self._to_model(job)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)

    async def get_by_id(self, *, job_id: UUID) -> GroupingExportJob | None:
        model = await self._session.get(GroupingExportJobModel, job_id)
        return self._to_job(model) if model else None

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> GroupingExportJob | None:
        result = await self._session.execute(
            select(GroupingExportJobModel).where(
                GroupingExportJobModel.upstream_job_id == upstream_job_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_job(model) if model else None

    async def get_latest_in_flight_for_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
    ) -> GroupingExportJob | None:
        result = await self._session.execute(
            select(GroupingExportJobModel)
            .where(
                GroupingExportJobModel.owner_user_id == owner_user_id,
                GroupingExportJobModel.draft_id == draft_id,
                GroupingExportJobModel.status.in_(
                    [
                        GroupingExportJobStatus.SUBMITTED.value,
                        GroupingExportJobStatus.PROCESSING.value,
                    ]
                ),
            )
            .order_by(
                GroupingExportJobModel.created_at.desc(),
                GroupingExportJobModel.updated_at.desc(),
            )
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_job(model) if model else None

    async def get_latest_downloadable_for_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
    ) -> GroupingExportJob | None:
        result = await self._session.execute(
            select(GroupingExportJobModel)
            .where(
                GroupingExportJobModel.owner_user_id == owner_user_id,
                GroupingExportJobModel.draft_id == draft_id,
                GroupingExportJobModel.status == GroupingExportJobStatus.SUCCEEDED.value,
                GroupingExportJobModel.vault_file_id.is_not(None),
            )
            .order_by(
                GroupingExportJobModel.created_at.desc(),
                GroupingExportJobModel.updated_at.desc(),
            )
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_job(model) if model else None

    async def update(self, *, job: GroupingExportJob) -> GroupingExportJob:
        model = await self._session.get(GroupingExportJobModel, job.id)
        if model is None:
            return job

        model.status = job.status.value
        model.upstream_job_id = job.upstream_job_id
        model.webhook_subscription_id = job.webhook_subscription_id
        model.webhook_secret = job.webhook_secret
        model.vault_file_id = job.vault_file_id
        model.error_message = job.error_message
        model.paper_size = job.paper_size.value if job.paper_size is not None else None
        model.output_filename = job.output_filename
        model.export_kind = job.export_kind.value
        model.roster_id = job.roster_id

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)
