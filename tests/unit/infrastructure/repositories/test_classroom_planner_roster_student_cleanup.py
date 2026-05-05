"""Repository tests for roster-student reference cleanup.

These tests verify the save-time roster edit cleanup that removes deleted
student ids from current draft assignments and bounded undo/redo snapshots.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
)
from skriptoteket.infrastructure.repositories.classroom_planner_roster_students import (
    PostgreSQLRosterStudentReferenceRepository,
)


def _execute_result(models: list[object]) -> Mock:
    result = Mock()
    result.scalars.return_value.all.return_value = models
    return result


def _draft_model(*, owner_id, roster_id, now: datetime) -> PlanDraftModel:
    return PlanDraftModel(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind="seating",
        template_id=uuid4(),
        smart_enabled=False,
        use_history=False,
        grouping_seating_distance_enabled=False,
        status="active",
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
        group_assignments=[
            GroupAssignmentModel(student_id="student-1", group_id="group-1"),
            GroupAssignmentModel(student_id="student-2", group_id="group-1"),
        ],
        seat_assignments=[
            SeatAssignmentModel(student_id="student-1", seat_id="seat-1"),
            SeatAssignmentModel(student_id="student-2", seat_id="seat-2"),
        ],
        history_stack=[
            {
                "groups": [],
                "group_assignments": [
                    {"student_id": "student-1", "group_id": "group-1"},
                    {"student_id": "student-2", "group_id": "group-1"},
                ],
                "seat_assignments": [
                    {"student_id": "student-1", "seat_id": "seat-1"},
                    {"student_id": "student-2", "seat_id": "seat-2"},
                ],
            }
        ],
        undo_index=0,
    )


@pytest.mark.asyncio
async def test_remove_student_references_for_roster_prunes_current_rows_and_history() -> None:
    session = AsyncMock()
    repo = PostgreSQLRosterStudentReferenceRepository(session)
    owner_id = uuid4()
    roster_id = uuid4()
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    updated_at = datetime(2026, 5, 6, tzinfo=timezone.utc)
    model = _draft_model(owner_id=owner_id, roster_id=roster_id, now=now)
    session.execute.return_value = _execute_result([model])

    await repo.remove_for_roster(
        owner_user_id=owner_id,
        roster_id=roster_id,
        student_ids={"student-1"},
        updated_at=updated_at,
    )

    assert [assignment.student_id for assignment in model.group_assignments] == ["student-2"]
    assert [assignment.student_id for assignment in model.seat_assignments] == ["student-2"]
    assert model.history_stack == [
        {
            "groups": [],
            "group_assignments": [{"student_id": "student-2", "group_id": "group-1"}],
            "seat_assignments": [{"student_id": "student-2", "seat_id": "seat-2"}],
        }
    ]
    assert model.updated_at == updated_at
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_student_references_for_roster_skips_empty_student_set() -> None:
    session = AsyncMock()
    repo = PostgreSQLRosterStudentReferenceRepository(session)

    await repo.remove_for_roster(
        owner_user_id=uuid4(),
        roster_id=uuid4(),
        student_ids=set(),
        updated_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
    )

    session.execute.assert_not_awaited()
    session.flush.assert_not_awaited()
