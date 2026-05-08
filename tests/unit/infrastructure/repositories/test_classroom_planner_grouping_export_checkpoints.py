"""Repository tests for grouping export checkpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.checkpoint_provenance import (
    CheckpointSourceKind,
)
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    NormalizedGroupingGroup,
    NormalizedGroupingSnapshot,
)
from skriptoteket.infrastructure.repositories.classroom_planner_grouping_export_checkpoints import (
    PostgreSQLGroupingExportCheckpointRepository,
)


def _checkpoint() -> GroupingExportCheckpoint:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return GroupingExportCheckpoint(
        id=uuid4(),
        roster_id=uuid4(),
        template_id=None,
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        assignment_hash="assignment-hash",
        grouping_snapshot=NormalizedGroupingSnapshot(
            groups=[NormalizedGroupingGroup(student_ids=["student-1", "student-2"])],
            ungrouped_student_ids=["student-3"],
        ),
        created_at=now,
    )


@pytest.mark.asyncio
async def test_create_persists_grouping_checkpoint_json_payloads() -> None:
    session = AsyncMock()
    session.add = Mock()
    repo = PostgreSQLGroupingExportCheckpointRepository(session)
    checkpoint = _checkpoint()

    persisted = await repo.create(checkpoint=checkpoint)

    assert persisted == checkpoint
    stored_model = session.add.call_args.args[0]
    assert stored_model.source_kind == CheckpointSourceKind.EXPORT_JOB.value
    assert stored_model.source_export_job_id == checkpoint.source_export_job_id
    assert stored_model.source_share_artifact_id is None
    assert stored_model.assignment_hash == checkpoint.assignment_hash
    assert stored_model.grouping_snapshot["ungrouped_student_ids"] == ["student-3"]
    assert session.flush.await_count == 1
    assert session.refresh.await_count == 1


@pytest.mark.asyncio
async def test_list_recent_for_roster_maps_models_to_domain_newest_first() -> None:
    session = AsyncMock()
    older = Mock(
        id=uuid4(),
        roster_id=uuid4(),
        template_id=None,
        source_draft_id=uuid4(),
        source_kind=CheckpointSourceKind.EXPORT_JOB.value,
        source_export_job_id=uuid4(),
        source_share_artifact_id=None,
        assignment_hash="assignment-older",
        grouping_snapshot={"groups": [], "ungrouped_student_ids": ["student-3"]},
        created_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
    )
    newer = Mock(
        id=uuid4(),
        roster_id=older.roster_id,
        template_id=None,
        source_draft_id=uuid4(),
        source_kind=CheckpointSourceKind.EXPORT_JOB.value,
        source_export_job_id=uuid4(),
        source_share_artifact_id=None,
        assignment_hash="assignment-newer",
        grouping_snapshot={"groups": [], "ungrouped_student_ids": []},
        created_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    scalar_result = Mock()
    scalar_result.scalars.return_value.all.return_value = [newer, older]
    session.execute.return_value = scalar_result
    repo = PostgreSQLGroupingExportCheckpointRepository(session)

    result = await repo.list_recent_for_roster(roster_id=older.roster_id)

    assert [checkpoint.assignment_hash for checkpoint in result] == [
        "assignment-newer",
        "assignment-older",
    ]
    statement = session.execute.call_args.args[0]
    assert "LIMIT 12" in str(statement.compile(compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_list_recent_for_roster_maps_share_artifact_provenance_to_domain() -> None:
    session = AsyncMock()
    share_artifact_id = uuid4()
    model = Mock(
        id=uuid4(),
        roster_id=uuid4(),
        template_id=None,
        source_draft_id=uuid4(),
        source_kind=CheckpointSourceKind.SHARE_ARTIFACT.value,
        source_export_job_id=None,
        source_share_artifact_id=share_artifact_id,
        assignment_hash="assignment-share",
        grouping_snapshot={"groups": [], "ungrouped_student_ids": []},
        created_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    scalar_result = Mock()
    scalar_result.scalars.return_value.all.return_value = [model]
    session.execute.return_value = scalar_result
    repo = PostgreSQLGroupingExportCheckpointRepository(session)

    result = await repo.list_recent_for_roster(roster_id=model.roster_id)

    assert len(result) == 1
    assert result[0].source_kind is CheckpointSourceKind.SHARE_ARTIFACT
    assert result[0].source_export_job_id is None
    assert result[0].source_share_artifact_id == share_artifact_id
