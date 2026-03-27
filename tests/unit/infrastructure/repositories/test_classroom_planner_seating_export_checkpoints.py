"""Repository tests for seating export checkpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomSeat,
    NormalizedSeatingSnapshot,
    NormalizedSeatPlacement,
    SeatingExportCheckpoint,
    SeatingRoomContextSnapshot,
)
from skriptoteket.infrastructure.repositories.classroom_planner_seating_export_checkpoints import (
    PostgreSQLSeatingExportCheckpointRepository,
)


def _scalar_one_or_none_result(value: object | None) -> Mock:
    result = Mock()
    result.scalar_one_or_none.return_value = value
    return result


def _checkpoint() -> SeatingExportCheckpoint:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return SeatingExportCheckpoint(
        id=uuid4(),
        roster_id=uuid4(),
        template_id=uuid4(),
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        room_context_hash="room-hash",
        assignment_hash="assignment-hash",
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


@pytest.mark.asyncio
async def test_create_persists_checkpoint_json_payloads() -> None:
    session = AsyncMock()
    session.add = Mock()
    repo = PostgreSQLSeatingExportCheckpointRepository(session)
    checkpoint = _checkpoint()

    persisted = await repo.create(checkpoint=checkpoint)

    assert persisted == checkpoint
    stored_model = session.add.call_args.args[0]
    assert stored_model.room_context_hash == checkpoint.room_context_hash
    assert stored_model.assignment_hash == checkpoint.assignment_hash
    assert stored_model.room_context["grid_cols"] == 14
    assert stored_model.seating_snapshot["unplaced_student_ids"] == ["student-2"]
    assert session.flush.await_count == 1
    assert session.refresh.await_count == 1


@pytest.mark.asyncio
async def test_get_latest_for_roster_and_room_context_maps_model_to_domain() -> None:
    session = AsyncMock()
    model = Mock(
        id=uuid4(),
        roster_id=uuid4(),
        template_id=uuid4(),
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        room_context_hash="room-hash",
        assignment_hash="assignment-hash",
        room_context={"grid_cols": 14, "grid_rows": 9, "seats": [], "fixtures": []},
        seating_snapshot={
            "placed_assignments": [{"seat_id": "seat-a", "student_id": "student-1"}],
            "unplaced_student_ids": ["student-2"],
        },
        created_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
    )
    session.execute.return_value = _scalar_one_or_none_result(model)
    repo = PostgreSQLSeatingExportCheckpointRepository(session)

    result = await repo.get_latest_for_roster_and_room_context(
        roster_id=model.roster_id,
        room_context_hash=model.room_context_hash,
    )

    assert result is not None
    assert result.assignment_hash == "assignment-hash"
    assert result.seating_snapshot.unplaced_student_ids == ["student-2"]
