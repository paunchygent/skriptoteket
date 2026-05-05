"""SQLAlchemy cleanup for roster student references.

Class-list edits can delete students that still appear in draft assignments or
history snapshots. The repository removes those stale ids without taking over
the broader draft persistence contract.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    PlanDraftModel,
)
from skriptoteket.protocols.classroom_planner import (
    RosterStudentReferenceRepositoryProtocol,
)


def _remove_student_references_from_snapshot(
    *,
    snapshot: dict[str, object],
    student_ids: set[str],
) -> tuple[dict[str, object], bool]:
    next_snapshot = dict(snapshot)
    changed = False
    for key in ("group_assignments", "seat_assignments"):
        assignments = snapshot.get(key)
        if not isinstance(assignments, list):
            continue
        filtered = [
            assignment
            for assignment in assignments
            if not (
                isinstance(assignment, dict)
                and isinstance(assignment.get("student_id"), str)
                and assignment["student_id"] in student_ids
            )
        ]
        if len(filtered) != len(assignments):
            next_snapshot[key] = filtered
            changed = True
    return next_snapshot, changed


class PostgreSQLRosterStudentReferenceRepository(RosterStudentReferenceRepositoryProtocol):
    """Remove deleted roster students from draft-local references."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def remove_for_roster(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        student_ids: set[str],
        updated_at: datetime,
    ) -> None:
        if not student_ids:
            return

        result = await self._session.execute(
            select(PlanDraftModel)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
            )
            .options(
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
            )
        )
        for model in result.scalars().all():
            if _remove_student_references_from_model(model=model, student_ids=student_ids):
                model.updated_at = updated_at
        await self._session.flush()


def _remove_student_references_from_model(
    *,
    model: PlanDraftModel,
    student_ids: set[str],
) -> bool:
    changed = False

    group_assignments = [
        assignment
        for assignment in model.group_assignments
        if assignment.student_id not in student_ids
    ]
    if len(group_assignments) != len(model.group_assignments):
        model.group_assignments = group_assignments
        changed = True

    seat_assignments = [
        assignment
        for assignment in model.seat_assignments
        if assignment.student_id not in student_ids
    ]
    if len(seat_assignments) != len(model.seat_assignments):
        model.seat_assignments = seat_assignments
        changed = True

    pruned_history = []
    for snapshot in model.history_stack or []:
        if not isinstance(snapshot, dict):
            pruned_history.append(snapshot)
            continue
        next_snapshot, snapshot_changed = _remove_student_references_from_snapshot(
            snapshot=snapshot,
            student_ids=student_ids,
        )
        pruned_history.append(next_snapshot)
        changed = changed or snapshot_changed
    if changed and model.history_stack is not None:
        model.history_stack = pruned_history

    return changed
