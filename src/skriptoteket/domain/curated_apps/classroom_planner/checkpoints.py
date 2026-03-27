"""Checkpoint models and hashing for classroom-planner export history.

This module defines the export-backed seating checkpoint contract used for
smart-history. It keeps checkpoint identity separate from both draft-local
undo/autosave history and roster-global smart rules while providing one
deterministic hashing strategy for normalized seating state and room context.
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import blake2b
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    RoomFixtureType,
)


class NormalizedSeatPlacement(BaseModel):
    """Represent one deterministic placed student assignment."""

    model_config = ConfigDict(frozen=True)

    seat_id: str
    student_id: str


class NormalizedRoomSeat(BaseModel):
    """Represent one seat inside the checkpointed room context."""

    model_config = ConfigDict(frozen=True)

    id: str
    x: int
    y: int
    zone: str | None = None


class NormalizedRoomFixture(BaseModel):
    """Represent one fixture inside the checkpointed room context."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: RoomFixtureType
    x: int
    y: int
    width: int
    height: int
    label: str | None = None


class SeatingRoomContextSnapshot(BaseModel):
    """Capture the normalized room context relevant to seating history."""

    model_config = ConfigDict(frozen=True)

    grid_cols: int
    grid_rows: int
    seats: list[NormalizedRoomSeat] = Field(default_factory=list)
    fixtures: list[NormalizedRoomFixture] = Field(default_factory=list)


class NormalizedSeatingSnapshot(BaseModel):
    """Capture the normalized teacher-approved seating state."""

    model_config = ConfigDict(frozen=True)

    placed_assignments: list[NormalizedSeatPlacement] = Field(default_factory=list)
    unplaced_student_ids: list[str] = Field(default_factory=list)


class SeatingExportCheckpoint(BaseModel):
    """Represent one explicit seating-history checkpoint created by export."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    roster_id: UUID
    template_id: UUID
    source_draft_id: UUID
    source_export_job_id: UUID
    room_context_hash: str
    assignment_hash: str
    room_context: SeatingRoomContextSnapshot
    seating_snapshot: NormalizedSeatingSnapshot
    created_at: datetime


def build_room_context_snapshot(
    *,
    workspace: ClassroomPlannerWorkspace,
) -> SeatingRoomContextSnapshot:
    """Normalize room geometry so checkpoint identity survives list ordering drift."""

    template = workspace.template
    if template is None:
        raise ValueError("Seating export checkpoints require a room template.")

    return SeatingRoomContextSnapshot(
        grid_cols=template.grid_cols,
        grid_rows=template.grid_rows,
        seats=[
            NormalizedRoomSeat(
                id=seat.id,
                x=seat.x,
                y=seat.y,
                zone=seat.zone,
            )
            for seat in sorted(template.seats, key=lambda seat: (seat.id, seat.x, seat.y))
        ],
        fixtures=[
            NormalizedRoomFixture(
                id=fixture.id,
                type=fixture.type,
                x=fixture.x,
                y=fixture.y,
                width=fixture.width,
                height=fixture.height,
                label=fixture.label,
            )
            for fixture in sorted(
                template.fixtures,
                key=lambda fixture: (
                    fixture.id,
                    fixture.type.value,
                    fixture.x,
                    fixture.y,
                    fixture.width,
                    fixture.height,
                    fixture.label or "",
                ),
            )
        ],
    )


def build_normalized_seating_snapshot(
    *,
    workspace: ClassroomPlannerWorkspace,
) -> NormalizedSeatingSnapshot:
    """Normalize placed and unplaced students into one deterministic snapshot."""

    placed_assignments = [
        NormalizedSeatPlacement(
            seat_id=assignment.seat_id,
            student_id=assignment.student_id,
        )
        for assignment in sorted(
            workspace.seat_assignments,
            key=lambda assignment: (assignment.seat_id, assignment.student_id),
        )
    ]
    placed_student_ids = {assignment.student_id for assignment in placed_assignments}
    unplaced_student_ids = sorted(
        student.id for student in workspace.roster.students if student.id not in placed_student_ids
    )
    return NormalizedSeatingSnapshot(
        placed_assignments=placed_assignments,
        unplaced_student_ids=unplaced_student_ids,
    )


def build_room_context_hash(*, room_context: SeatingRoomContextSnapshot) -> str:
    """Hash the normalized room context for checkpoint scoping."""

    return _hash_payload(_room_context_payload(room_context=room_context))


def build_assignment_hash(*, seating_snapshot: NormalizedSeatingSnapshot) -> str:
    """Hash the normalized seating state for dedupe."""

    return _hash_payload(_seating_snapshot_payload(seating_snapshot=seating_snapshot))


def _room_context_payload(*, room_context: SeatingRoomContextSnapshot) -> dict[str, object]:
    return {
        "grid_cols": room_context.grid_cols,
        "grid_rows": room_context.grid_rows,
        "seats": [seat.model_dump(mode="json") for seat in room_context.seats],
        "fixtures": [
            {
                **fixture.model_dump(mode="json"),
                "type": fixture.type.value,
            }
            for fixture in room_context.fixtures
        ],
    }


def _seating_snapshot_payload(*, seating_snapshot: NormalizedSeatingSnapshot) -> dict[str, object]:
    return {
        "placed_assignments": [
            placement.model_dump(mode="json") for placement in seating_snapshot.placed_assignments
        ],
        "unplaced_student_ids": seating_snapshot.unplaced_student_ids,
    }


def _hash_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return blake2b(encoded, digest_size=16).hexdigest()
