"""Domain models for the Classroom Planner curated app.

This module defines the active classroom-planner aggregates shared by the
domain, application handlers, repositories, and bespoke SPA API contract. The
current fundamentals contract keeps reusable roster and room assets separate
from mutable draft state for groups, seat assignments, and teacher notes.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Student(BaseModel):
    """Represent one student in a teacher-owned roster."""

    model_config = ConfigDict(frozen=True)

    id: str
    display_name: str


class Roster(BaseModel):
    """Represent a teacher-owned roster."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    name: str
    students: list[Student]
    created_at: datetime
    updated_at: datetime


class Seat(BaseModel):
    """Represent one seat in a room template."""

    model_config = ConfigDict(frozen=True)

    id: str
    x: int
    y: int
    zone: str | None = None


class RoomFixtureType(StrEnum):
    """Enumerate supported decorative room fixtures."""

    WHITEBOARD = "whiteboard"
    TEACHER_DESK = "teacher_desk"
    WINDOW = "window"
    DOOR = "door"


class RoomFixture(BaseModel):
    """Represent one visual room fixture."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: RoomFixtureType
    x: int
    y: int
    width: int
    height: int
    label: str | None = None


class RoomTemplate(BaseModel):
    """Represent a teacher-owned room template."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    name: str
    seats: list[Seat]
    fixtures: list[RoomFixture] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DraftGroup(BaseModel):
    """Represent a stable group bucket inside one draft."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    name: str
    sort_order: int


class GroupAssignment(BaseModel):
    """Represent one student-to-group assignment."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    group_id: str


class SeatAssignment(BaseModel):
    """Represent one student-to-seat assignment."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    seat_id: str


class StudentPlanningMeta(BaseModel):
    """Represent teacher-only notes and seating/grouping inputs for a student."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    teacher_proximity: int = 0
    stability_preference: int = 0
    preferred_zone: str | None = None
    avoid_zone: str | None = None
    notes: str | None = None


class PlanDraftStatus(StrEnum):
    """Enumerate mutable draft lifecycle states."""

    ACTIVE = "active"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class PlanDraftKind(StrEnum):
    """Enumerate the teacher-facing draft kinds."""

    GROUPING = "grouping"
    SEATING = "seating"


class PlanDraft(BaseModel):
    """Represent the mutable root draft record."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    roster_id: UUID
    draft_kind: PlanDraftKind
    template_id: UUID | None = None
    status: PlanDraftStatus = PlanDraftStatus.ACTIVE
    revision: int = 0
    last_opened_at: datetime
    created_at: datetime
    updated_at: datetime


class DraftWorkspace(BaseModel):
    """Represent the full mutable draft workspace."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    student_planning_meta: list[StudentPlanningMeta] = Field(default_factory=list)


class ClassroomPlannerWorkspace(BaseModel):
    """Represent the hydrated planner context returned to the frontend."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    roster: Roster
    template: RoomTemplate | None = None
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    student_planning_meta: list[StudentPlanningMeta] = Field(default_factory=list)


class ResumablePlanDraft(BaseModel):
    """Represent the latest resumable draft CTA payload."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    roster_name: str
    template_name: str | None = None
