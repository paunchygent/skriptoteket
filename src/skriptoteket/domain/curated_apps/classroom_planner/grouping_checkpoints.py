"""Grouping checkpoint models and hashing for classroom-planner history.

Purpose:
    Define the export-backed grouping-history contract for smart grouping.

Relationships:
    - consumed by future grouping export persistence and smart-grouping history
      reads
    - intentionally label-insensitive so grouping identity depends on student
      partitions rather than draft-local group ids or names
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import blake2b
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    Roster,
)


class NormalizedGroupingGroup(BaseModel):
    """Represent one deterministic grouping bucket without draft-local labels."""

    model_config = ConfigDict(frozen=True)

    student_ids: list[str] = Field(default_factory=list)


class NormalizedGroupingSnapshot(BaseModel):
    """Capture the normalized teacher-approved grouping state."""

    model_config = ConfigDict(frozen=True)

    groups: list[NormalizedGroupingGroup] = Field(default_factory=list)
    ungrouped_student_ids: list[str] = Field(default_factory=list)


class GroupingExportCheckpoint(BaseModel):
    """Represent one explicit grouping-history checkpoint created by export."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    roster_id: UUID
    template_id: UUID | None = None
    source_draft_id: UUID
    source_export_job_id: UUID
    assignment_hash: str
    grouping_snapshot: NormalizedGroupingSnapshot
    created_at: datetime


def build_normalized_grouping_snapshot(
    *,
    roster: Roster,
    group_assignments: list[GroupAssignment],
) -> NormalizedGroupingSnapshot:
    """Normalize placed and unplaced grouping state into one deterministic snapshot."""

    student_ids_by_group: dict[str, list[str]] = {}
    assigned_student_ids: set[str] = set()
    for assignment in sorted(
        group_assignments,
        key=lambda assignment: (assignment.group_id, assignment.student_id),
    ):
        student_ids_by_group.setdefault(assignment.group_id, []).append(assignment.student_id)
        assigned_student_ids.add(assignment.student_id)
    return NormalizedGroupingSnapshot(
        groups=[
            NormalizedGroupingGroup(student_ids=student_ids)
            for _, student_ids in sorted(student_ids_by_group.items(), key=lambda item: item[0])
        ],
        ungrouped_student_ids=sorted(
            student.id for student in roster.students if student.id not in assigned_student_ids
        ),
    )


def build_grouping_assignment_hash(*, grouping_snapshot: NormalizedGroupingSnapshot) -> str:
    """Hash one normalized grouping partition for dedupe and identity."""

    payload = {
        "groups": [
            {"student_ids": sorted(group.student_ids)}
            for group in sorted(
                grouping_snapshot.groups,
                key=lambda group: tuple(sorted(group.student_ids)),
            )
        ],
        "ungrouped_student_ids": sorted(grouping_snapshot.ungrouped_student_ids),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return blake2b(encoded, digest_size=16).hexdigest()
