"""Unit tests for grouping export job completion and checkpoint recording."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import GroupingExportJobFinalizer
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportJob,
    GroupingExportJobStatus,
    GroupingExportKind,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    NormalizedGroupingGroup,
    NormalizedGroupingSnapshot,
)
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.classroom_planner import GroupingExportCheckpointRepositoryProtocol
from skriptoteket.protocols.classroom_planner_exports import GroupingExportJobRepositoryProtocol
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


def _job() -> GroupingExportJob:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return GroupingExportJob(
        id=uuid4(),
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
        output_filename="klass-7a-gruppindelning.xlsx",
        status=GroupingExportJobStatus.SUBMITTED,
        created_at=now,
        updated_at=now,
    )


def _checkpoint(
    *, roster_id, draft_id, export_job_id, assignment_hash: str
) -> GroupingExportCheckpoint:
    return GroupingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        template_id=None,
        source_draft_id=draft_id,
        source_export_job_id=export_job_id,
        assignment_hash=assignment_hash,
        grouping_snapshot=NormalizedGroupingSnapshot(
            groups=[NormalizedGroupingGroup(student_ids=["student-1", "student-2"])],
            ungrouped_student_ids=["student-3"],
        ),
        created_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )


def _settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000,
        VAULT_MAX_TOTAL_BYTES=10_000_000,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_local_success_records_grouping_checkpoint_when_latest_differs() -> None:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    job = _job()
    checkpoints = AsyncMock(spec=GroupingExportCheckpointRepositoryProtocol)
    checkpoints.list_recent_for_roster.return_value = []
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
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
        draft_id=job.draft_id,
        export_job_id=job.id,
        assignment_hash="hash-1",
    )

    finalizer = GroupingExportJobFinalizer(
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
    )

    assert result.status is GroupingExportJobStatus.SUCCEEDED
    checkpoints.create.assert_awaited_once_with(checkpoint=checkpoint)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_local_success_skips_grouping_checkpoint_when_assignment_hash_matches() -> (
    None
):
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    job = _job()
    checkpoints = AsyncMock(spec=GroupingExportCheckpointRepositoryProtocol)
    jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
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
        draft_id=job.draft_id,
        export_job_id=job.id,
        assignment_hash="hash-1",
    )
    checkpoints.list_recent_for_roster.return_value = [
        checkpoint.model_copy(update={"source_export_job_id": uuid4()})
    ]

    finalizer = GroupingExportJobFinalizer(
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
    )

    checkpoints.create.assert_not_awaited()
