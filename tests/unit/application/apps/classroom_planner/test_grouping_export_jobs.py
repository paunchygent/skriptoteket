"""Behavior tests for classroom-planner grouping export jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateGroupingExportJobHandler,
    DownloadGroupingExportJobHandler,
    GetRecoverableGroupingExportJobForDraftHandler,
    GroupingExportJobFinalizer,
    GroupingExportKind,
    GroupingExportPaperSize,
    PrepareGroupingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportJob,
    GroupingExportJobStatus,
    GroupingExportPresentation,
    PreparedGroupingExportContract,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftHistoryStatus,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    Roster,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    GroupingPdfRendererProtocol,
    GroupingXlsxRendererProtocol,
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


def _prepared_contract() -> PreparedGroupingExportContract:
    draft_id = uuid4()
    roster_id = uuid4()
    return PreparedGroupingExportContract(
        grouping_draft_id=draft_id,
        roster_id=roster_id,
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
        presentation=GroupingExportPresentation(
            draft_id=draft_id,
            class_name="Klass 7A",
            title="Gruppindelning",
            filename_stem="klass-7a-gruppindelning",
            groups=(),
        ),
    )


def _grouping_workspace(*, owner_user_id) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    roster_id = uuid4()
    draft_id = uuid4()
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=draft_id,
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING,
            template_id=None,
            status=PlanDraftStatus.ACTIVE,
            revision=1,
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
                Student(id="student-2", display_name="Bo Berg"),
                Student(id="student-3", display_name="Grace Hopper"),
            ],
            created_at=now,
            updated_at=now,
        ),
        template=None,
        groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=1)],
        group_assignments=[
            GroupAssignment(student_id="student-1", group_id="group-1"),
            GroupAssignment(student_id="student-2", group_id="group-1"),
        ],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _job(
    *,
    owner_user_id,
    status: GroupingExportJobStatus,
    vault_file_id=None,
) -> GroupingExportJob:
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    prepared = _prepared_contract()
    return GroupingExportJob(
        id=uuid4(),
        owner_user_id=owner_user_id,
        draft_id=prepared.grouping_draft_id,
        roster_id=prepared.roster_id,
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
        output_filename="klass-7a-gruppindelning.xlsx",
        status=status,
        vault_file_id=vault_file_id,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_export_job_persists_placeholder_submitted_job():
    actor = make_user()
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    job_id = uuid4()
    prepare = AsyncMock(spec=PrepareGroupingExportHandler)
    prepare.load_workspace.return_value = _grouping_workspace(owner_user_id=actor.id)
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
    jobs.create.side_effect = lambda *, job: job
    pdf_renderer = AsyncMock(spec=GroupingPdfRendererProtocol)
    xlsx_renderer = AsyncMock(spec=GroupingXlsxRendererProtocol)
    xlsx_renderer.render.return_value = b"PK\x03\x04"
    finalizer = AsyncMock(spec=GroupingExportJobFinalizer)
    finalizer.complete_local_success.side_effect = lambda *, job, content, checkpoint, filename: (
        job.model_copy(
            update={
                "status": GroupingExportJobStatus.SUCCEEDED,
                "vault_file_id": uuid4(),
            }
        )
    )

    handler = CreateGroupingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        pdf_renderer=pdf_renderer,
        xlsx_renderer=xlsx_renderer,
        finalizer=finalizer,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(job_id),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
    )

    persisted_job = jobs.create.await_args.kwargs["job"]
    assert persisted_job.status is GroupingExportJobStatus.SUBMITTED
    assert persisted_job.output_filename.endswith(".xlsx")
    assert str(job_id).split("-", maxsplit=1)[0] in persisted_job.output_filename
    assert result.status is GroupingExportJobStatus.SUCCEEDED
    pdf_renderer.render.assert_not_called()
    xlsx_renderer.render.assert_called_once()
    finalizer.complete_local_success.assert_awaited_once()
    assert result.download_url is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_pdf_job_renders_local_pdf_and_completes_successfully():
    actor = make_user()
    now = datetime(2026, 3, 26, tzinfo=timezone.utc)
    job_id = uuid4()
    prepare = AsyncMock(spec=PrepareGroupingExportHandler)
    prepare.load_workspace.return_value = _grouping_workspace(owner_user_id=actor.id)
    prepare.handle.return_value = _prepared_contract().model_copy(
        update={
            "export_kind": GroupingExportKind.PDF,
            "paper_size": GroupingExportPaperSize.A4_PORTRAIT,
        }
    )
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
    jobs.create.side_effect = lambda *, job: job
    pdf_renderer = AsyncMock(spec=GroupingPdfRendererProtocol)
    pdf_renderer.render.return_value = b"%PDF-1.7"
    xlsx_renderer = AsyncMock(spec=GroupingXlsxRendererProtocol)
    finalizer = AsyncMock(spec=GroupingExportJobFinalizer)
    finalizer.complete_local_success.side_effect = lambda *, job, content, checkpoint, filename: (
        job.model_copy(
            update={
                "status": GroupingExportJobStatus.SUCCEEDED,
                "vault_file_id": uuid4(),
            }
        )
    )

    handler = CreateGroupingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        pdf_renderer=pdf_renderer,
        xlsx_renderer=xlsx_renderer,
        finalizer=finalizer,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(job_id),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        export_kind=GroupingExportKind.PDF,
        paper_size=GroupingExportPaperSize.A4_PORTRAIT,
    )

    persisted_job = jobs.create.await_args.kwargs["job"]
    assert persisted_job.output_filename.endswith(".pdf")
    assert result.status is GroupingExportJobStatus.SUCCEEDED
    pdf_renderer.render.assert_called_once()
    xlsx_renderer.render.assert_not_called()
    finalizer.complete_local_success.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recoverable_grouping_export_prefers_in_flight_job():
    actor = make_user()
    in_flight_job = _job(
        owner_user_id=actor.id,
        status=GroupingExportJobStatus.PROCESSING,
    )
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
    jobs.get_latest_in_flight_for_draft.return_value = in_flight_job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)

    handler = GetRecoverableGroupingExportJobForDraftHandler(
        jobs=jobs,
        vault_files=vault_files,
        uow=_DummyUow(),
    )

    result = await handler.handle(actor=actor, draft_id=in_flight_job.draft_id)

    assert result is not None
    assert result.status is GroupingExportJobStatus.PROCESSING
    jobs.get_latest_downloadable_for_draft.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_grouping_export_job_returns_xlsx_artifact():
    actor = make_user()
    file_id = uuid4()
    job = _job(
        owner_user_id=actor.id,
        status=GroupingExportJobStatus.SUCCEEDED,
        vault_file_id=file_id,
    )
    vault_file = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="klass-7a-gruppindelning.xlsx",
        bytes=1234,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        created_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
    )
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
    jobs.get_by_id.return_value = job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.get_by_id.return_value = vault_file
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    vault_storage.read_file.return_value = b"PK\x03\x04"

    handler = DownloadGroupingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=_DummyUow(),
    )

    filename, media_type, content = await handler.handle(actor=actor, job_id=job.id)

    assert filename == "klass-7a-gruppindelning.xlsx"
    assert media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert content == b"PK\x03\x04"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_grouping_export_job_rejects_placeholder_job_without_artifact():
    actor = make_user()
    job = _job(
        owner_user_id=actor.id,
        status=GroupingExportJobStatus.SUBMITTED,
        vault_file_id=None,
    )
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
    jobs.get_by_id.return_value = job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_storage = AsyncMock(spec=VaultStorageProtocol)

    handler = DownloadGroupingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=_DummyUow(),
    )

    with pytest.raises(DomainError) as error:
        await handler.handle(actor=actor, job_id=job.id)

    assert error.value.code == ErrorCode.VALIDATION_ERROR
