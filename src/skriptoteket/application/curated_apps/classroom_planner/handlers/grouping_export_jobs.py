"""Application handlers for classroom-planner grouping export jobs.

Purpose:
    Orchestrate the grouping export lane: validate the requested export family,
    prepare the shared presentation contract, persist dedicated grouping export
    jobs, and expose recoverable in-flight state. In PR-0140 the XLSX lane
    renders locally and completes through Vault while the PDF lane remains
    placeholder scaffolding for the later renderer slice.

Relationships:
    - Reuses `PrepareGroupingExportHandler` for the canonical presentation seam.
    - Persists dedicated export jobs through `GroupingExportJobRepositoryProtocol`.
    - Uses `GroupingExportJobFinalizer` to keep Vault persistence separate from
      job orchestration.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportJob,
    GroupingExportJobResult,
    GroupingExportJobStatus,
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportVaultArtifact,
    build_grouping_export_presentation,
    build_grouping_xlsx_view_model,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import ClassroomPlannerWorkspace
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    GroupingXlsxRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol

from .grouping_export_job_completion import GroupingExportJobFinalizer
from .grouping_exports import PrepareGroupingExportHandler


class CreateGroupingExportJobHandler:
    """Create one explicit grouping export job in the correct artifact lane."""

    def __init__(
        self,
        *,
        prepare: PrepareGroupingExportHandler,
        jobs: GroupingExportJobRepositoryProtocol,
        xlsx_renderer: GroupingXlsxRendererProtocol,
        finalizer: GroupingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._prepare = prepare
        self._jobs = jobs
        self._xlsx_renderer = xlsx_renderer
        self._finalizer = finalizer
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        export_kind: GroupingExportKind,
        paper_size: GroupingExportPaperSize | None,
    ) -> GroupingExportJobResult:
        if export_kind is GroupingExportKind.XLSX:
            return await self._handle_xlsx_export(actor=actor, draft_id=draft_id)

        prepared = await self._prepare.handle(
            draft_id=draft_id,
            owner_user_id=actor.id,
            export_kind=export_kind,
            paper_size=paper_size,
        )
        output_filename = _output_filename_for_request(
            filename_stem=prepared.presentation.filename_stem,
            export_kind=export_kind,
            paper_size=paper_size,
        )
        job = await self._create_submitted_job(
            owner_user_id=actor.id,
            draft_id=prepared.grouping_draft_id,
            roster_id=prepared.roster_id,
            export_kind=export_kind,
            paper_size=paper_size,
            output_filename=output_filename,
        )
        return await build_grouping_job_result(job=job, vault_files=None)

    async def _handle_xlsx_export(
        self,
        *,
        actor: User,
        draft_id: UUID,
    ) -> GroupingExportJobResult:
        workspace = await self._prepare.load_workspace(
            draft_id=draft_id,
            owner_user_id=actor.id,
        )
        presentation = build_grouping_export_presentation(workspace=workspace)
        view_model = build_grouping_xlsx_view_model(
            presentation=presentation,
            generated_at=self._clock.now(),
            unassigned_student_names=_unassigned_student_names(workspace),
        )
        job = await self._create_submitted_job(
            owner_user_id=actor.id,
            draft_id=workspace.draft.id,
            roster_id=workspace.roster.id,
            export_kind=GroupingExportKind.XLSX,
            paper_size=None,
            output_filename=view_model.output_filename,
        )
        try:
            artifact_bytes = self._xlsx_renderer.render(view_model=view_model)
            completed_job = await self._finalizer.complete_local_success(
                job=job,
                content=artifact_bytes,
                filename=view_model.output_filename,
            )
        except Exception:
            await self._finalizer.mark_failed(
                job=job,
                error_message="Kunde inte skapa Excel-exporten just nu. Försök igen.",
            )
            raise
        return await build_grouping_job_result(job=completed_job, vault_files=None)

    async def _create_submitted_job(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        roster_id: UUID,
        export_kind: GroupingExportKind,
        paper_size: GroupingExportPaperSize | None,
        output_filename: str,
    ) -> GroupingExportJob:
        now = self._clock.now()
        job_id = self._id_generator.new_uuid()
        async with self._uow:
            return await self._jobs.create(
                job=GroupingExportJob(
                    id=job_id,
                    owner_user_id=owner_user_id,
                    draft_id=draft_id,
                    roster_id=roster_id,
                    export_kind=export_kind,
                    paper_size=paper_size,
                    output_filename=_stamp_output_filename(
                        filename=output_filename,
                        stamp_source=job_id,
                    ),
                    status=GroupingExportJobStatus.SUBMITTED,
                    created_at=now,
                    updated_at=now,
                )
            )


class GetGroupingExportJobHandler:
    """Load one grouping export job for the owning teacher."""

    def __init__(
        self,
        *,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._vault_files = vault_files
        self._uow = uow

    async def handle(self, *, actor: User, job_id: UUID) -> GroupingExportJobResult:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("GroupingExportJob", str(job_id))
        return await build_grouping_job_result(job=job, vault_files=self._vault_files)


class GetRecoverableGroupingExportJobForDraftHandler:
    """Load the latest recoverable grouping export job for the active draft."""

    def __init__(
        self,
        *,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._vault_files = vault_files
        self._uow = uow

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
    ) -> GroupingExportJobResult | None:
        async with self._uow:
            in_flight_job = await self._jobs.get_latest_in_flight_for_draft(
                owner_user_id=actor.id,
                draft_id=draft_id,
            )
        if in_flight_job is not None:
            return await build_grouping_job_result(job=in_flight_job, vault_files=self._vault_files)

        async with self._uow:
            downloadable_job = await self._jobs.get_latest_downloadable_for_draft(
                owner_user_id=actor.id,
                draft_id=draft_id,
            )
        if downloadable_job is None:
            return None
        result = await build_grouping_job_result(
            job=downloadable_job,
            vault_files=self._vault_files,
        )
        return result if result.download_url is not None else None


class DownloadGroupingExportJobHandler:
    """Download the finished grouping export artifact once later slices produce it."""

    def __init__(
        self,
        *,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._vault_files = vault_files
        self._vault_storage = vault_storage
        self._uow = uow

    async def handle(self, *, actor: User, job_id: UUID) -> tuple[str, str, bytes]:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
            if job is None or job.owner_user_id != actor.id:
                raise not_found("GroupingExportJob", str(job_id))
            if job.vault_file_id is None:
                raise validation_error("Exporten är inte klar ännu.")
            vault_file = await self._vault_files.get_by_id(file_id=job.vault_file_id)
            if vault_file is None or vault_file.user_id != actor.id:
                raise not_found("VaultFile", str(job.vault_file_id))
        return (
            vault_file.name,
            _media_type_for_filename(vault_file.name),
            await self._vault_storage.read_file(
                user_id=actor.id,
                file_id=vault_file.id,
            ),
        )


async def build_grouping_job_result(
    *,
    job: GroupingExportJob,
    vault_files: VaultFileRepositoryProtocol | None,
) -> GroupingExportJobResult:
    """Build the public grouping job result from one persisted export job."""

    vault_artifact = None
    if job.vault_file_id is not None and vault_files is not None:
        vault_file = await vault_files.get_by_id(file_id=job.vault_file_id)
        if vault_file is not None:
            vault_artifact = GroupingExportVaultArtifact(
                file_id=vault_file.id,
                name=vault_file.name,
                bytes=vault_file.bytes,
                created_at=vault_file.created_at,
            )
    download_url = (
        f"/api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/{job.id}/download"
        if vault_artifact is not None
        else None
    )
    return GroupingExportJobResult(
        job_id=job.id,
        draft_id=job.draft_id,
        export_kind=job.export_kind,
        paper_size=job.paper_size,
        status=job.status,
        created_at=job.created_at,
        download_url=download_url,
        vault_artifact=vault_artifact,
        error=job.error_message,
    )


def _output_filename_for_request(
    *,
    filename_stem: str,
    export_kind: GroupingExportKind,
    paper_size: GroupingExportPaperSize | None,
) -> str:
    """Build the teacher-facing filename for one grouping export request."""

    if export_kind is GroupingExportKind.XLSX:
        return f"{filename_stem}.xlsx"
    if paper_size is not GroupingExportPaperSize.A4_PORTRAIT:
        raise validation_error("PDF-export kräver A4 stående i den här versionen.")
    return f"{filename_stem}-a4-portrait.pdf"


def _stamp_output_filename(*, filename: str, stamp_source: UUID) -> str:
    """Append a short deterministic stamp so repeated exports keep unique names."""

    parsed = Path(filename or "klassrumskarta.xlsx")
    suffix = parsed.suffix or ".xlsx"
    stem = parsed.stem or "klassrumskarta"
    stamp = str(stamp_source).split("-", maxsplit=1)[0]
    return f"{stem}-{stamp}{suffix}"


def _unassigned_student_names(
    workspace: ClassroomPlannerWorkspace,
) -> tuple[str, ...]:
    """Collect students who are still ungrouped in the current workspace."""

    assigned_student_ids = {assignment.student_id for assignment in workspace.group_assignments}
    return tuple(
        sorted(
            (
                student.display_name
                for student in workspace.roster.students
                if student.id not in assigned_student_ids
            ),
            key=lambda name: name.casefold(),
        )
    )


def _media_type_for_filename(filename: str) -> str:
    """Map the stored export artifact name to an HTTP media type."""

    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix == ".pdf":
        return "application/pdf"
    return "application/octet-stream"
