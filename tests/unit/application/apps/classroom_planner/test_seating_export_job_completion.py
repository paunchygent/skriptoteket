"""Unit tests for seating export job completion and checkpoint recording.

This module verifies that successful seating exports record export-backed
history checkpoints only when the latest checkpoint in the same room context
actually differs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import SeatingExportJobFinalizer
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJob,
    SeatingExportJobStatus,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomSeat,
    NormalizedSeatingSnapshot,
    NormalizedSeatPlacement,
    SeatingExportCheckpoint,
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.classroom_planner import SeatingExportCheckpointRepositoryProtocol
from skriptoteket.protocols.classroom_planner_exports import SeatingExportJobRepositoryProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


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


def _job() -> SeatingExportJob:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return SeatingExportJob(
        id=uuid4(),
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
        template_id=uuid4(),
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        output_filename="klass-7a-a3.pdf",
        status=SeatingExportJobStatus.SUBMITTED,
        created_at=now,
        updated_at=now,
    )


def _checkpoint(
    *,
    roster_id,
    template_id,
    draft_id,
    export_job_id,
    assignment_hash: str,
) -> SeatingExportCheckpoint:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return SeatingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        template_id=template_id,
        source_draft_id=draft_id,
        source_export_job_id=export_job_id,
        room_context_hash="room-hash-1",
        assignment_hash=assignment_hash,
        room_context=SeatingRoomContextSnapshot(
            grid_cols=14,
            grid_rows=9,
            seats=[NormalizedRoomSeat(id="seat-a", x=0, y=0, zone="front")],
            fixtures=[],
        ),
        seating_snapshot=NormalizedSeatingSnapshot(
            placed_assignments=[NormalizedSeatPlacement(seat_id="seat-a", student_id="student-1")],
            unplaced_student_ids=["student-2"],
        ),
        created_at=now,
    )


def _settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000,
        VAULT_MAX_TOTAL_BYTES=10_000_000,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_local_success_records_checkpoint_when_latest_differs() -> None:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    job = _job()
    checkpoints = AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.update.side_effect = lambda *, job: job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_file_id = uuid4()
    vault_files.create.return_value = VaultFile(
        id=vault_file_id,
        user_id=job.owner_user_id,
        name=job.output_filename,
        bytes=4,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=now,
        deleted_at=None,
    )
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=job.owner_user_id,
        bytes_total=0,
        updated_at=now,
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    checkpoints.get_latest_for_roster_and_room_context.return_value = None
    checkpoint = _checkpoint(
        roster_id=job.roster_id,
        template_id=job.template_id,
        draft_id=job.draft_id,
        export_job_id=job.id,
        assignment_hash="hash-1",
    )

    finalizer = SeatingExportJobFinalizer(
        jobs=jobs,
        checkpoints=checkpoints,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(vault_file_id),
        settings=_settings(),
    )

    result = await finalizer.complete_local_success(
        job=job,
        content=b"data",
        checkpoint=checkpoint,
        correlation_id="corr-1",
    )

    assert result.status is SeatingExportJobStatus.SUCCEEDED
    checkpoints.create.assert_awaited_once_with(checkpoint=checkpoint)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_local_success_skips_checkpoint_when_latest_assignment_hash_matches() -> (
    None
):
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    job = _job()
    checkpoints = AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.update.side_effect = lambda *, job: job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_file_id = uuid4()
    vault_files.create.return_value = VaultFile(
        id=vault_file_id,
        user_id=job.owner_user_id,
        name=job.output_filename,
        bytes=4,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=now,
        deleted_at=None,
    )
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=job.owner_user_id,
        bytes_total=0,
        updated_at=now,
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    checkpoint = _checkpoint(
        roster_id=job.roster_id,
        template_id=job.template_id,
        draft_id=job.draft_id,
        export_job_id=job.id,
        assignment_hash="hash-1",
    )
    checkpoints.get_latest_for_roster_and_room_context.return_value = checkpoint.model_copy(
        update={"source_export_job_id": uuid4()}
    )

    finalizer = SeatingExportJobFinalizer(
        jobs=jobs,
        checkpoints=checkpoints,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(vault_file_id),
        settings=_settings(),
    )

    await finalizer.complete_local_success(
        job=job,
        content=b"data",
        checkpoint=checkpoint,
        correlation_id="corr-2",
    )

    checkpoints.create.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_local_success_keeps_geometry_based_identity_across_template_ids() -> None:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    job = _job()
    checkpoints = AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.update.side_effect = lambda *, job: job
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_file_id = uuid4()
    vault_files.create.return_value = VaultFile(
        id=vault_file_id,
        user_id=job.owner_user_id,
        name=job.output_filename,
        bytes=4,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=now,
        deleted_at=None,
    )
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=job.owner_user_id,
        bytes_total=0,
        updated_at=now,
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    checkpoint = _checkpoint(
        roster_id=job.roster_id,
        template_id=job.template_id,
        draft_id=job.draft_id,
        export_job_id=job.id,
        assignment_hash="hash-1",
    )
    checkpoints.get_latest_for_roster_and_room_context.return_value = checkpoint.model_copy(
        update={
            "template_id": uuid4(),
            "source_export_job_id": uuid4(),
        }
    )

    finalizer = SeatingExportJobFinalizer(
        jobs=jobs,
        checkpoints=checkpoints,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(vault_file_id),
        settings=_settings(),
    )

    await finalizer.complete_local_success(
        job=job,
        content=b"data",
        checkpoint=checkpoint,
        correlation_id="corr-3",
    )

    checkpoints.create.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_failed_does_not_create_checkpoint() -> None:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    job = _job()
    checkpoints = AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.update.side_effect = lambda *, job: job

    finalizer = SeatingExportJobFinalizer(
        jobs=jobs,
        checkpoints=checkpoints,
        vault_files=AsyncMock(spec=VaultFileRepositoryProtocol),
        vault_usage=AsyncMock(spec=VaultUsageRepositoryProtocol),
        vault_storage=AsyncMock(spec=VaultStorageProtocol),
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
        settings=_settings(),
    )

    result = await finalizer.mark_failed(
        job=job,
        error_message="kunde inte exportera",
        correlation_id="corr-4",
    )

    assert result.status is SeatingExportJobStatus.FAILED
    checkpoints.get_latest_for_roster_and_room_context.assert_not_awaited()
    checkpoints.create.assert_not_awaited()
