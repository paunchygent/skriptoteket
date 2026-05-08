"""Application handlers for classroom-planner seating export jobs.

Purpose:
    Orchestrate the explicit seating export lane: prepare the canonical poster
    scene, render export-owned HTML/CSS, convert the PDF locally, and deliver
    the finished artifact from Vault while preserving the same teacher-facing
    export-job seam for PDF and XLSX.

Relationships:
    - Reuses `PrepareSeatingExportHandler` from the PR-0118 contract seam.
    - Persists dedicated export jobs through `SeatingExportJobRepositoryProtocol`.
    - Uses local seating PDF/XLSX renderers plus Vault-backed finalization.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJob,
    SeatingExportJobResult,
    SeatingExportJobStatus,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    seating_xlsx_view_model,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoint_provenance import (
    CheckpointSourceKind,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportJobRepositoryProtocol,
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
    SeatingXlsxRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

from .checkpoint_recorders import build_seating_checkpoint
from .seating_export_job_completion import SeatingExportJobFinalizer
from .seating_export_job_support import build_job_result
from .seating_exports import PrepareSeatingExportHandler


class CreateSeatingExportJobHandler:
    """Create one explicit seating export job in the correct local artifact lane."""

    def __init__(
        self,
        *,
        prepare: PrepareSeatingExportHandler,
        jobs: SeatingExportJobRepositoryProtocol,
        pdf_renderer: SeatingPdfRendererProtocol,
        poster_renderer: SeatingPosterRendererProtocol,
        xlsx_renderer: SeatingXlsxRendererProtocol,
        finalizer: SeatingExportJobFinalizer,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._prepare = prepare
        self._jobs = jobs
        self._pdf_renderer = pdf_renderer
        self._poster_renderer = poster_renderer
        self._xlsx_renderer = xlsx_renderer
        self._finalizer = finalizer
        self._vault_files = vault_files
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        export_kind: SeatingExportKind,
        layout_id: SeatingExportLayoutId | None,
        paper_size: SeatingExportPaperSize | None,
        correlation_id: str | None,
    ) -> SeatingExportJobResult:
        if export_kind is SeatingExportKind.XLSX:
            return await self._handle_xlsx_export(
                actor=actor,
                draft_id=draft_id,
                correlation_id=correlation_id,
            )
        return await self._handle_pdf_export(
            actor=actor,
            draft_id=draft_id,
            layout_id=layout_id,
            paper_size=paper_size,
            correlation_id=correlation_id,
        )

    async def _handle_pdf_export(
        self,
        *,
        actor: User,
        draft_id: UUID,
        layout_id: SeatingExportLayoutId | None,
        paper_size: SeatingExportPaperSize | None,
        correlation_id: str | None,
    ) -> SeatingExportJobResult:
        if layout_id is None or paper_size is None:
            raise validation_error("PDF-export kräver layout och pappersstorlek.")

        workspace = await self._prepare.load_workspace(
            draft_id=draft_id,
            owner_user_id=actor.id,
        )
        prepared = self._prepare.build_prepared_contract(
            workspace=workspace,
            export_kind=SeatingExportKind.PDF,
            layout_id=layout_id,
        )
        rendered = self._poster_renderer.render(
            request=SeatingPosterRenderRequest(
                roster_name=prepared.roster_name,
                template_name=prepared.template_name,
                paper_size=paper_size,
                scene=prepared.poster_scene,
            )
        )
        job = await self._create_job_record(
            actor=actor,
            draft_id=prepared.seating_draft_id,
            roster_id=prepared.roster_id,
            template_id=prepared.template_id,
            export_kind=prepared.export_kind,
            layout_id=prepared.layout_id,
            paper_size=paper_size,
            output_filename=rendered.output_filename,
        )
        try:
            artifact_bytes = self._pdf_renderer.render(bundle=rendered)
            completed_job = await self._finalizer.complete_local_success(
                job=job,
                content=artifact_bytes,
                checkpoint=_build_export_checkpoint_candidate(
                    workspace=workspace,
                    export_job_id=job.id,
                    exported_at=job.created_at,
                    checkpoint_id=self._id_generator.new_uuid(),
                ),
                filename=rendered.output_filename,
                correlation_id=correlation_id,
            )
        except Exception:
            await self._finalizer.mark_failed(
                job=job,
                error_message="Kunde inte skapa PDF-exporten just nu. Försök igen.",
                correlation_id=correlation_id,
            )
            raise
        return await build_job_result(job=completed_job, vault_files=None)

    async def _handle_xlsx_export(
        self,
        *,
        actor: User,
        draft_id: UUID,
        correlation_id: str | None,
    ) -> SeatingExportJobResult:
        workspace = await self._prepare.load_workspace(
            draft_id=draft_id,
            owner_user_id=actor.id,
        )
        view_model = seating_xlsx_view_model.build_seating_xlsx_view_model(workspace=workspace)
        artifact_bytes = self._xlsx_renderer.render(view_model=view_model)
        job = await self._create_job_record(
            actor=actor,
            draft_id=workspace.draft.id,
            roster_id=workspace.roster.id,
            template_id=workspace.template.id if workspace.template is not None else None,
            export_kind=SeatingExportKind.XLSX,
            layout_id=None,
            paper_size=None,
            output_filename=view_model.output_filename,
        )
        completed_job = await self._finalizer.complete_local_success(
            job=job,
            content=artifact_bytes,
            checkpoint=_build_export_checkpoint_candidate(
                workspace=workspace,
                export_job_id=job.id,
                exported_at=job.created_at,
                checkpoint_id=self._id_generator.new_uuid(),
            ),
            correlation_id=correlation_id,
        )
        return await build_job_result(job=completed_job, vault_files=self._vault_files)

    async def _create_job_record(
        self,
        *,
        actor: User,
        draft_id: UUID,
        roster_id: UUID,
        template_id: UUID | None,
        export_kind: SeatingExportKind,
        layout_id: SeatingExportLayoutId | None,
        paper_size: SeatingExportPaperSize | None,
        output_filename: str,
    ) -> SeatingExportJob:
        if template_id is None:
            raise validation_error("Välj klassrum innan du exporterar sittschemat.")
        now = self._clock.now()
        job_id = self._id_generator.new_uuid()
        async with self._uow:
            return await self._jobs.create(
                job=SeatingExportJob(
                    id=job_id,
                    owner_user_id=actor.id,
                    draft_id=draft_id,
                    roster_id=roster_id,
                    template_id=template_id,
                    export_kind=export_kind,
                    layout_id=layout_id,
                    paper_size=paper_size,
                    output_filename=_stamp_output_filename(
                        filename=output_filename,
                        stamp_source=job_id,
                    ),
                    status=SeatingExportJobStatus.SUBMITTED,
                    created_at=now,
                    updated_at=now,
                )
            )


class _BaseSeatingExportJobReadHandler:
    """Shared read support for seating export job status handlers."""

    def __init__(
        self,
        *,
        jobs: SeatingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._vault_files = vault_files
        self._uow = uow

    async def _build_result(self, *, job: SeatingExportJob) -> SeatingExportJobResult:
        return await build_job_result(job=job, vault_files=self._vault_files)

    async def _load_owner_job(self, *, actor: User, job_id: UUID) -> SeatingExportJob:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("SeatingExportJob", str(job_id))
        return job


class GetSeatingExportJobHandler(_BaseSeatingExportJobReadHandler):
    """Load one export job for the owning teacher."""

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> SeatingExportJobResult:
        del correlation_id
        job = await self._load_owner_job(actor=actor, job_id=job_id)
        return await self._build_result(job=job)


class GetRecoverableSeatingExportJobForDraftHandler(_BaseSeatingExportJobReadHandler):
    """Load the latest recoverable export job for the active seating draft."""

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        correlation_id: str | None,
    ) -> SeatingExportJobResult | None:
        del correlation_id
        in_flight_job = await self._load_latest_in_flight_job(actor=actor, draft_id=draft_id)
        if in_flight_job is not None:
            return await self._build_result(job=in_flight_job)

        downloadable_job = await self._load_latest_downloadable_job(actor=actor, draft_id=draft_id)
        if downloadable_job is None:
            return None
        result = await self._build_result(job=downloadable_job)
        return result if result.download_url is not None else None

    async def _load_latest_in_flight_job(
        self,
        *,
        actor: User,
        draft_id: UUID,
    ) -> SeatingExportJob | None:
        async with self._uow:
            return await self._jobs.get_latest_in_flight_for_draft(
                owner_user_id=actor.id,
                draft_id=draft_id,
            )

    async def _load_latest_downloadable_job(
        self,
        *,
        actor: User,
        draft_id: UUID,
    ) -> SeatingExportJob | None:
        async with self._uow:
            return await self._jobs.get_latest_downloadable_for_draft(
                owner_user_id=actor.id,
                draft_id=draft_id,
            )


def _stamp_output_filename(*, filename: str, stamp_source: UUID) -> str:
    """Append a short deterministic stamp so repeated exports keep unique names."""

    parsed = Path(filename or "klassrumskarta.pdf")
    suffix = parsed.suffix or ".pdf"
    stem = parsed.stem or "klassrumskarta"
    stamp = str(stamp_source).split("-", maxsplit=1)[0]
    return f"{stem}-{stamp}{suffix}"


def _build_export_checkpoint_candidate(
    *,
    workspace: ClassroomPlannerWorkspace,
    export_job_id: UUID,
    exported_at,
    checkpoint_id: UUID,
) -> SeatingExportCheckpoint:
    """Build the checkpoint candidate recorded for a successful seating export."""

    return build_seating_checkpoint(
        workspace=workspace,
        checkpoint_id=checkpoint_id,
        created_at=exported_at,
        source_kind=CheckpointSourceKind.EXPORT_JOB,
        source_export_job_id=export_job_id,
    )
