"""Domain models for the Classroom Planner curated app.

This module defines the active classroom-planner aggregates shared by the
domain, application handlers, repositories, and bespoke SPA API contract. The
current fundamentals contract separates roster-owned smart rules from
draft-local arrangement state so seating/grouping workspaces can reuse one
class rule set across multiple drafts.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_ROOM_GRID_COLS = 14
DEFAULT_ROOM_GRID_ROWS = 9


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
    ROUND_TABLE = "round_table"
    SQUARE_TABLE = "square_table"
    BENCH = "bench"


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
    grid_cols: int = Field(default=DEFAULT_ROOM_GRID_COLS, ge=1)
    grid_rows: int = Field(default=DEFAULT_ROOM_GRID_ROWS, ge=1)
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
    name_is_custom: bool = False


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
    """Represent teacher-only notes for a student, kept separate from smart rules."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    notes: str | None = None


class StudentSeatingPreference(BaseModel):
    """Represent per-student seating-only preference inputs."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    near_teacher: bool = False


class RelationshipKind(StrEnum):
    """Enumerate supported relationship rule types."""

    KEEP_NEAR = "keep_near"
    KEEP_APART = "keep_apart"


class RelationshipRule(BaseModel):
    """Represent a relationship constraint between two or more students."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    kind: RelationshipKind
    student_ids: list[str] = Field(min_length=2)


class RosterSmartRules(BaseModel):
    """Represent roster-owned smart rules shared across drafts for one class."""

    model_config = ConfigDict(frozen=True)

    roster_id: UUID
    revision: int = 0
    seating_preferences: list[StudentSeatingPreference] = Field(default_factory=list)
    relationship_rules: list[RelationshipRule] = Field(default_factory=list)


class PlanDraftStatus(StrEnum):
    """Enumerate mutable draft lifecycle states."""

    ACTIVE = "active"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class PlanDraftKind(StrEnum):
    """Enumerate the teacher-facing draft kinds."""

    GROUPING = "grouping"
    SEATING = "seating"


class ClassroomSelectionMode(StrEnum):
    """Describe how a draft kind relates to classroom selection at entry time."""

    OPTIONAL = "optional"
    REQUIRED = "required"


class PlanDraft(BaseModel):
    """Represent the mutable root draft record."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    roster_id: UUID
    draft_kind: PlanDraftKind
    template_id: UUID | None = None
    smart_enabled: bool = False
    use_history: bool = False
    grouping_seating_distance_enabled: bool = False
    status: PlanDraftStatus = PlanDraftStatus.ACTIVE
    revision: int = 0
    last_opened_at: datetime
    created_at: datetime
    updated_at: datetime


class DraftWorkspace(BaseModel):
    """Represent the full fundamentals planning context."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    student_planning_meta: list[StudentPlanningMeta] = Field(default_factory=list)
    history_status: DraftHistoryStatus = Field(
        default_factory=lambda: DraftHistoryStatus(can_undo=False, can_redo=False)
    )


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
    history_status: DraftHistoryStatus = Field(
        default_factory=lambda: DraftHistoryStatus(can_undo=False, can_redo=False)
    )


class ResumablePlanDraft(BaseModel):
    """Represent the latest resumable draft CTA payload."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    roster_name: str
    template_name: str | None = None


class DraftHistoryStatus(BaseModel):
    """Represent the undo/redo availability for one active draft."""

    model_config = ConfigDict(frozen=True)

    can_undo: bool
    can_redo: bool


class TaskEntryOption(BaseModel):
    """Represent one task-entry rule surfaced by the class workspace contract."""

    model_config = ConfigDict(frozen=True)

    draft_kind: PlanDraftKind
    classroom_selection_mode: ClassroomSelectionMode


class PlanDraftSummary(BaseModel):
    """Represent a compact draft summary for class-workspace read models."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    draft_kind: PlanDraftKind
    template_id: UUID | None = None
    template_name: str | None = None
    status: PlanDraftStatus
    revision: int
    last_opened_at: datetime
    updated_at: datetime


class ClassWorkspaceRosterSummary(BaseModel):
    """Represent compact class identity details for the class workspace."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    student_count: int


class ClassWorkspaceDraftSummary(BaseModel):
    """Represent active and historical draft summaries for one class."""

    model_config = ConfigDict(frozen=True)

    active_grouping_draft: PlanDraftSummary | None = None
    active_seating_draft: PlanDraftSummary | None = None
    grouping_history: list[PlanDraftSummary] = Field(default_factory=list)
    seating_history: list[PlanDraftSummary] = Field(default_factory=list)


class ClassWorkspaceSummary(BaseModel):
    """Represent the class-first workspace summary returned to the frontend."""

    model_config = ConfigDict(frozen=True)

    roster: ClassWorkspaceRosterSummary
    task_entry_options: list[TaskEntryOption] = Field(default_factory=list)
    active_grouping_draft: PlanDraftSummary | None = None
    active_seating_draft: PlanDraftSummary | None = None
    grouping_history: list[PlanDraftSummary] = Field(default_factory=list)
    seating_history: list[PlanDraftSummary] = Field(default_factory=list)
