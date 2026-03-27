"""Behavior tests for classroom-planner seating export jobs.

Purpose:
    Guard the PR-0146 local seating export cutover so PDF and XLSX jobs finish
    inside Skriptoteket while the teacher-facing job and download contract
    stays unchanged.

Relationships:
    - Exercises `CreateSeatingExportJobHandler` and the related read/download
      handlers.
    - Uses protocol mocks instead of patching implementation details.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateSeatingExportJobHandler,
    DownloadSeatingExportJobHandler,
    GetRecoverableSeatingExportJobForDraftHandler,
    GetSeatingExportJobHandler,
    PrepareSeatingExportHandler,
    SeatingExportJobFinalizer,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneRoom,
    PreparedSeatingExportContract,
    RenderedSeatingPosterBundle,
    SeatingExportJob,
    SeatingExportJobStatus,
    SeatingPosterScene,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportJobRepositoryProtocol,
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
    SeatingXlsxRendererProtocol,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol
from tests.fixtures.identity_fixtures import make_user


class _DummyUow:
    async def __aenter__(self) -> _DummyUow:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _FixedIdGenerator:
    def __init__(self, value) -> None:
        self._value = value

    def new_uuid(self):
        return self._value


def _prepared_contract() -> PreparedSeatingExportContract:
    draft_id = uuid4()
    return PreparedSeatingExportContract(
        seating_draft_id=draft_id,
        roster_id=uuid4(),
        roster_name="Klass 7A",
        template_id=uuid4(),
        template_name="Sal A",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=14, grid_rows=9),
            seats=[],
            fixtures=[],
        ),
    )


def _workspace(*, owner_user_id) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    draft_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=draft_id,
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            status=PlanDraftStatus.ACTIVE,
            revision=4,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="Klass 7A",
            students=[
                Student(id="student-1", display_name="Ada Lovelace"),
                Student(id="student-2", display_name="Linus Torvalds"),
            ],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=template_id,
            owner_user_id=owner_user_id,
            name="Sal A",
            seats=[Seat(id="seat-1", x=0, y=0)],
            fixtures=[],
            created_at=now,
            updated_at=now,
        ),
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-1")],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _job(
    *,
    owner_user_id,
    status: SeatingExportJobStatus,
    export_kind: SeatingExportKind = SeatingExportKind.PDF,
    paper_size: SeatingExportPaperSize | None = SeatingExportPaperSize.A3_LANDSCAPE,
    vault_file_id=None,
) -> SeatingExportJob:
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    prepared = _prepared_contract()
    return SeatingExportJob(
        id=uuid4(),
        owner_user_id=owner_user_id,
        draft_id=prepared.seating_draft_id,
        roster_id=prepared.roster_id,
        template_id=prepared.template_id,
        export_kind=export_kind,
        layout_id=prepared.layout_id if export_kind is SeatingExportKind.PDF else None,
        paper_size=paper_size if export_kind is SeatingExportKind.PDF else None,
        output_filename=(
            "klass-7a-a3.pdf" if export_kind is SeatingExportKind.PDF else "klass-7a.xlsx"
        ),
        status=status,
        vault_file_id=vault_file_id,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_pdf_job_renders_locally_and_completes_successfully():
    actor = make_user()
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    job_id = uuid4()
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    workspace = _workspace(owner_user_id=actor.id)
    prepare.load_workspace.return_value = workspace
    assert workspace.template is not None
    template = workspace.template
    prepare.build_prepared_contract.return_value = _prepared_contract().model_copy(
        update={
            "seating_draft_id": workspace.draft.id,
            "roster_id": workspace.roster.id,
            "template_id": template.id,
            "template_name": template.name,
            "roster_name": workspace.roster.name,
        }
    )
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.create.side_effect = lambda *, job: job
    pdf_renderer = MagicMock(spec=SeatingPdfRendererProtocol)
    pdf_renderer.render.return_value = b"%PDF-1.7"
    poster_renderer = MagicMock(spec=SeatingPosterRendererProtocol)
    poster_renderer.render.return_value = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content="<html><body>Poster</body></html>",
        css_filename="poster.css",
        css_content="body { color: black; }",
        resource_files=[],
        output_filename="klass-7a-a3.pdf",
    )
    xlsx_renderer = MagicMock(spec=SeatingXlsxRendererProtocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    finalizer.complete_local_success.side_effect = (
        lambda *, job, content, checkpoint, filename, correlation_id: job.model_copy(
            update={
                "status": SeatingExportJobStatus.SUCCEEDED,
                "vault_file_id": uuid4(),
            }
        )
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        pdf_renderer=pdf_renderer,
        poster_renderer=poster_renderer,
        xlsx_renderer=xlsx_renderer,
        finalizer=finalizer,
        vault_files=AsyncMock(spec=VaultFileRepositoryProtocol),
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(job_id),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        correlation_id="corr-1",
    )

    persisted_job = jobs.create.await_args.kwargs["job"]
    assert persisted_job.status is SeatingExportJobStatus.SUBMITTED
    assert persisted_job.output_filename.endswith(".pdf")
    assert str(job_id).split("-", maxsplit=1)[0] in persisted_job.output_filename
    assert result.status is SeatingExportJobStatus.SUCCEEDED
    poster_renderer.render.assert_called_once()
    pdf_renderer.render.assert_called_once()
    xlsx_renderer.render.assert_not_called()
    finalizer.complete_local_success.assert_awaited_once()
    checkpoint = finalizer.complete_local_success.await_args.kwargs["checkpoint"]
    assert checkpoint.roster_id == workspace.roster.id
    assert checkpoint.template_id == template.id
    assert result.download_url is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_pdf_job_marks_job_failed_when_local_rendering_crashes():
    actor = make_user()
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    workspace = _workspace(owner_user_id=actor.id)
    prepare.load_workspace.return_value = workspace
    assert workspace.template is not None
    template = workspace.template
    prepare.build_prepared_contract.return_value = _prepared_contract().model_copy(
        update={
            "seating_draft_id": workspace.draft.id,
            "roster_id": workspace.roster.id,
            "template_id": template.id,
            "template_name": template.name,
            "roster_name": workspace.roster.name,
        }
    )
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.create.side_effect = lambda *, job: job
    pdf_renderer = MagicMock(spec=SeatingPdfRendererProtocol)
    pdf_renderer.render.side_effect = RuntimeError("boom")
    poster_renderer = MagicMock(spec=SeatingPosterRendererProtocol)
    poster_renderer.render.return_value = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content="<html><body>Poster</body></html>",
        css_filename="poster.css",
        css_content="body { color: black; }",
        resource_files=[],
        output_filename="klass-7a-a3.pdf",
    )
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        pdf_renderer=pdf_renderer,
        poster_renderer=poster_renderer,
        xlsx_renderer=MagicMock(spec=SeatingXlsxRendererProtocol),
        finalizer=finalizer,
        vault_files=AsyncMock(spec=VaultFileRepositoryProtocol),
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
    )

    with pytest.raises(RuntimeError, match="boom"):
        await handler.handle(
            actor=actor,
            draft_id=uuid4(),
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            correlation_id="corr-2",
        )

    finalizer.mark_failed.assert_awaited_once()
    error_message = finalizer.mark_failed.await_args.kwargs["error_message"]
    assert error_message == "Kunde inte skapa PDF-exporten just nu. Försök igen."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_xlsx_job_keeps_local_export_flow():
    actor = make_user()
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    workspace = _workspace(owner_user_id=actor.id)
    prepare.load_workspace.return_value = workspace
    assert workspace.template is not None
    template = workspace.template
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.create.side_effect = lambda *, job: job
    xlsx_renderer = MagicMock(spec=SeatingXlsxRendererProtocol)
    xlsx_renderer.render.return_value = b"PK\x03\x04"
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)

    def _complete_local_success(*, job, content, checkpoint, correlation_id):
        del content, checkpoint, correlation_id
        return job.model_copy(
            update={
                "status": SeatingExportJobStatus.SUCCEEDED,
                "vault_file_id": uuid4(),
            }
        )

    finalizer.complete_local_success.side_effect = _complete_local_success
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.get_by_id.return_value = VaultFile(
        id=uuid4(),
        user_id=actor.id,
        name="klass-7a.xlsx",
        bytes=4,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=now,
        deleted_at=None,
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        pdf_renderer=MagicMock(spec=SeatingPdfRendererProtocol),
        poster_renderer=MagicMock(spec=SeatingPosterRendererProtocol),
        xlsx_renderer=xlsx_renderer,
        finalizer=finalizer,
        vault_files=vault_files,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        export_kind=SeatingExportKind.XLSX,
        layout_id=None,
        paper_size=None,
        correlation_id="corr-3",
    )

    assert result.export_kind is SeatingExportKind.XLSX
    xlsx_renderer.render.assert_called_once()
    finalizer.complete_local_success.assert_awaited_once()
    checkpoint = finalizer.complete_local_success.await_args.kwargs["checkpoint"]
    assert checkpoint.assignment_hash
    assert checkpoint.roster_id == workspace.roster.id
    assert checkpoint.template_id == template.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_seating_export_job_returns_saved_vault_download_when_present():
    actor = make_user()
    job = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=uuid4(),
    )
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.get_by_id.return_value = job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.get_by_id.return_value = VaultFile(
        id=job.vault_file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=1234,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
        deleted_at=None,
    )

    handler = GetSeatingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        uow=_DummyUow(),
    )

    result = await handler.handle(
        actor=actor,
        job_id=job.id,
        correlation_id="corr-4",
    )

    assert result.status is SeatingExportJobStatus.SUCCEEDED
    assert result.download_url is not None
    assert result.vault_artifact is not None
    assert result.vault_artifact.name == "klass-7a-a3.pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recoverable_seating_export_prefers_in_flight_job():
    actor = make_user()
    in_flight = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    downloadable = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=uuid4(),
    )
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.get_latest_in_flight_for_draft.return_value = in_flight
    jobs.get_latest_downloadable_for_draft.return_value = downloadable

    handler = GetRecoverableSeatingExportJobForDraftHandler(
        jobs=jobs,
        vault_files=AsyncMock(spec=VaultFileRepositoryProtocol),
        uow=_DummyUow(),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        correlation_id="corr-5",
    )

    assert result is not None
    assert result.job_id == in_flight.id
    jobs.get_latest_downloadable_for_draft.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_seating_export_job_returns_pdf_payload():
    actor = make_user()
    file_id = uuid4()
    job = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=file_id,
    )
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.get_by_id.return_value = job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.get_by_id.return_value = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=4,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
        deleted_at=None,
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    vault_storage.read_file.return_value = b"%PDF"

    handler = DownloadSeatingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=_DummyUow(),
    )

    filename, media_type, content = await handler.handle(actor=actor, job_id=job.id)

    assert filename == "klass-7a-a3.pdf"
    assert media_type == "application/pdf"
    assert content == b"%PDF"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_seating_export_job_rejects_unfinished_job():
    actor = make_user()
    job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING, vault_file_id=None)
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.get_by_id.return_value = job

    handler = DownloadSeatingExportJobHandler(
        jobs=jobs,
        vault_files=AsyncMock(spec=VaultFileRepositoryProtocol),
        vault_storage=AsyncMock(spec=VaultStorageProtocol),
        uow=_DummyUow(),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job.id)

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
