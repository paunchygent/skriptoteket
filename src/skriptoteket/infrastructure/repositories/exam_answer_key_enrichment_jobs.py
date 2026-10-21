"""PostgreSQL repository for machine answer-key enrichment jobs.

Purpose:
    Persist and claim the execution-worker jobs that produce machine-proposed
    answer keys, using the same FOR UPDATE SKIP LOCKED claim discipline as the
    tool-run execution queue.

Relationships:
    Implements ``ExamAnswerKeyEnrichmentJobRepositoryProtocol`` and the
    workspace suggestion lookups of ``ExamWorkspaceSuggestionJobQueryProtocol``
    on a request-scoped ``AsyncSession``; commit/rollback is owned by the UoW.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import Select, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamWorkspaceSuggestionJobQueryProtocol,
)


class PostgreSQLExamAnswerKeyEnrichmentJobRepository(
    ExamAnswerKeyEnrichmentJobRepositoryProtocol, ExamWorkspaceSuggestionJobQueryProtocol
):
    """Postgres enrichment-job ledger with SKIP LOCKED claims."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        model = ExamAnswerKeyEnrichmentJobModel(
            id=job.id,
            source_kind=job.source_kind.value,
            owner_user_id=job.owner_user_id,
            status=job.status.value,
            input_filename=job.input_filename,
            source_dxe=job.source_dxe,
            source_docx=job.source_docx,
            workspace_lineage_id=job.workspace_lineage_id,
            workspace_document_revision=job.workspace_document_revision,
            workspace_course_key=job.workspace_course_key,
            workspace_request_json=job.workspace_request_json,
            workspace_suggestions_json=job.workspace_suggestions_json,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            available_at=job.available_at,
            locked_by=job.locked_by,
            locked_until=job.locked_until,
            last_error=job.last_error,
            ai_limit=job.ai_limit.value if job.ai_limit is not None else None,
            diagnostics=list(job.diagnostics),
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)

    async def update(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        expected_worker_id: str | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        model = await self._session.get(ExamAnswerKeyEnrichmentJobModel, job.id)
        if model is None:
            raise not_found("ExamAnswerKeyEnrichmentJob", str(job.id))
        if expected_worker_id is not None and model.locked_by != expected_worker_id:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Answer-key enrichment worker lease is no longer owned.",
            )
        model.status = job.status.value
        model.source_docx = job.source_docx
        model.source_dxe = job.source_dxe
        model.workspace_course_key = job.workspace_course_key
        model.workspace_suggestions_json = job.workspace_suggestions_json
        model.attempts = job.attempts
        model.max_attempts = job.max_attempts
        model.available_at = job.available_at
        model.locked_by = job.locked_by
        model.locked_until = job.locked_until
        model.last_error = job.last_error
        model.ai_limit = job.ai_limit.value if job.ai_limit is not None else None
        model.diagnostics = list(job.diagnostics)
        # conversion_progress is written only by set_conversion_progress.
        model.updated_at = job.updated_at
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)

    async def set_conversion_progress(
        self, *, job_id: UUID, progress: dict[str, JsonValue]
    ) -> None:
        """Replace the job's persisted conversion progress; never commits."""
        model = await self._session.get(ExamAnswerKeyEnrichmentJobModel, job_id)
        if model is None:
            raise not_found("ExamAnswerKeyEnrichmentJob", str(job_id))
        model.conversion_progress = progress
        await self._session.flush()

    async def get_conversion_view(self, *, job_id: UUID) -> ExamWorkspaceConversionJobView | None:
        stmt = select(
            ExamAnswerKeyEnrichmentJobModel.id,
            ExamAnswerKeyEnrichmentJobModel.owner_user_id,
            ExamAnswerKeyEnrichmentJobModel.source_kind,
            ExamAnswerKeyEnrichmentJobModel.status,
            ExamAnswerKeyEnrichmentJobModel.workspace_lineage_id,
            ExamAnswerKeyEnrichmentJobModel.last_error,
            ExamAnswerKeyEnrichmentJobModel.ai_limit,
            ExamAnswerKeyEnrichmentJobModel.conversion_progress,
        ).where(ExamAnswerKeyEnrichmentJobModel.id == job_id)
        row = (await self._session.execute(stmt)).one_or_none()
        return (
            ExamWorkspaceConversionJobView.model_validate(row, from_attributes=True)
            if row
            else None
        )

    async def lock_conversion_view_by_lineage(
        self, *, owner_user_id: UUID, workspace_lineage_id: UUID
    ) -> ExamWorkspaceConversionJobView | None:
        stmt = (
            select(
                ExamAnswerKeyEnrichmentJobModel.id,
                ExamAnswerKeyEnrichmentJobModel.owner_user_id,
                ExamAnswerKeyEnrichmentJobModel.source_kind,
                ExamAnswerKeyEnrichmentJobModel.status,
                ExamAnswerKeyEnrichmentJobModel.workspace_lineage_id,
                ExamAnswerKeyEnrichmentJobModel.last_error,
                ExamAnswerKeyEnrichmentJobModel.ai_limit,
                ExamAnswerKeyEnrichmentJobModel.conversion_progress,
            )
            .where(
                ExamAnswerKeyEnrichmentJobModel.source_kind.in_(
                    (
                        ExamAnswerKeySourceKind.DOCX_IMPORT.value,
                        ExamAnswerKeySourceKind.DIGIEXAM_IMPORT.value,
                    )
                ),
                ExamAnswerKeyEnrichmentJobModel.owner_user_id == owner_user_id,
                ExamAnswerKeyEnrichmentJobModel.workspace_lineage_id == workspace_lineage_id,
            )
            .with_for_update(read=True)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        return (
            ExamWorkspaceConversionJobView.model_validate(row, from_attributes=True)
            if row
            else None
        )

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        stmt = select(ExamAnswerKeyEnrichmentJobModel).where(
            ExamAnswerKeyEnrichmentJobModel.id == job_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ExamAnswerKeyEnrichmentJob.model_validate(model) if model else None

    async def get_by_id_for_update(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        stmt = (
            select(ExamAnswerKeyEnrichmentJobModel)
            .where(ExamAnswerKeyEnrichmentJobModel.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ExamAnswerKeyEnrichmentJob.model_validate(model) if model else None

    async def get_latest_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        stmt = (
            self._workspace_jobs(
                owner_user_id=owner_user_id,
                workspace_lineage_id=workspace_lineage_id,
                workspace_document_revision=workspace_document_revision,
            )
            .order_by(
                ExamAnswerKeyEnrichmentJobModel.created_at.desc(),
                ExamAnswerKeyEnrichmentJobModel.id.desc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return ExamAnswerKeyEnrichmentJob.model_validate(model) if model else None

    async def get_active_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
        workspace_request_json: dict[str, JsonValue],
    ) -> ExamAnswerKeyEnrichmentJob | None:
        stmt = (
            self._workspace_jobs(
                owner_user_id=owner_user_id,
                workspace_lineage_id=workspace_lineage_id,
                workspace_document_revision=workspace_document_revision,
            )
            .where(
                ExamAnswerKeyEnrichmentJobModel.status.in_(
                    (
                        ExamAnswerKeyEnrichmentJobStatus.QUEUED.value,
                        ExamAnswerKeyEnrichmentJobStatus.RUNNING.value,
                    )
                ),
                ExamAnswerKeyEnrichmentJobModel.workspace_request_json == workspace_request_json,
            )
            .order_by(ExamAnswerKeyEnrichmentJobModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return ExamAnswerKeyEnrichmentJob.model_validate(model) if model else None

    async def lock_workspace_requests(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> None:
        # Released when the owning UoW commits or rolls back. The key leaves out
        # the sent content: equal requests compare by JSONB equality, which a
        # string hash of the content would not respect.
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {
                "lock_key": (
                    f"exam-workspace-suggestion:{owner_user_id}:"
                    f"{workspace_lineage_id}:{workspace_document_revision}"
                )
            },
        )

    @staticmethod
    def _workspace_jobs(
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> Select[tuple[ExamAnswerKeyEnrichmentJobModel]]:
        return select(ExamAnswerKeyEnrichmentJobModel).where(
            ExamAnswerKeyEnrichmentJobModel.source_kind == ExamAnswerKeySourceKind.WORKSPACE.value,
            ExamAnswerKeyEnrichmentJobModel.owner_user_id == owner_user_id,
            ExamAnswerKeyEnrichmentJobModel.workspace_lineage_id == workspace_lineage_id,
            ExamAnswerKeyEnrichmentJobModel.workspace_document_revision
            == workspace_document_revision,
        )

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise ValueError("worker_id is required")
        stmt = (
            select(ExamAnswerKeyEnrichmentJobModel)
            .where(
                ExamAnswerKeyEnrichmentJobModel.attempts
                < ExamAnswerKeyEnrichmentJobModel.max_attempts
            )
            .where(
                ExamAnswerKeyEnrichmentJobModel.status
                == ExamAnswerKeyEnrichmentJobStatus.QUEUED.value
            )
            .where(ExamAnswerKeyEnrichmentJobModel.available_at <= now)
            .order_by(ExamAnswerKeyEnrichmentJobModel.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if source_kind is not None:
            stmt = stmt.where(ExamAnswerKeyEnrichmentJobModel.source_kind == source_kind.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = ExamAnswerKeyEnrichmentJobStatus.RUNNING.value
        model.attempts = model.attempts + 1
        model.locked_by = normalized_worker_id
        model.locked_until = now + lease_ttl
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)

    async def claim_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        """Take one RUNNING job whose worker lease expired, for fail-closing.

        The row stays locked until the caller's transaction commits, so the
        fail-close transition is atomic with this selection.
        """
        stmt = (
            select(ExamAnswerKeyEnrichmentJobModel)
            .where(
                ExamAnswerKeyEnrichmentJobModel.status
                == ExamAnswerKeyEnrichmentJobStatus.RUNNING.value
            )
            .where(ExamAnswerKeyEnrichmentJobModel.locked_until.is_not(None))
            .where(ExamAnswerKeyEnrichmentJobModel.locked_until < now)
            .order_by(ExamAnswerKeyEnrichmentJobModel.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if source_kind is not None:
            stmt = stmt.where(ExamAnswerKeyEnrichmentJobModel.source_kind == source_kind.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.locked_by = worker_id
        model.locked_until = now + lease_ttl
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        renewed_id = await self._session.scalar(
            update(ExamAnswerKeyEnrichmentJobModel)
            .where(
                ExamAnswerKeyEnrichmentJobModel.id == job_id,
                ExamAnswerKeyEnrichmentJobModel.status
                == ExamAnswerKeyEnrichmentJobStatus.RUNNING.value,
                ExamAnswerKeyEnrichmentJobModel.locked_by == worker_id,
            )
            .values(locked_until=now + lease_ttl, updated_at=now)
            .returning(ExamAnswerKeyEnrichmentJobModel.id)
        )
        return renewed_id is not None
