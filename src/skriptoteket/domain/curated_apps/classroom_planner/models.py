"""Domain models for the Classroom Planner curated app.

This module defines the typed aggregates that connect the classroom planner
domain, application handlers, repositories, and bespoke SPA API contract. It
keeps roster/template identity separate from draft-scoped planning state such as
groups, assignments, teacher-only metadata, constraints, validation findings,
suggestion outputs, and immutable arrangement snapshots.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LessonModePreset(BaseModel):
    """Represent a predefined lesson mode preset."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str


LESSON_MODE_PRESETS: tuple[LessonModePreset, ...] = (
    LessonModePreset(id="seating", name="Sittplatsschema"),
    LessonModePreset(id="group_work", name="Gruppering"),
)


def is_valid_lesson_mode_id(*, lesson_mode_id: str) -> bool:
    """Return whether a lesson mode id exists in the bootstrap catalog."""

    return any(preset.id == lesson_mode_id for preset in LESSON_MODE_PRESETS)


class ClassroomPlannerBootstrapPayload(BaseModel):
    """Represent the initialization payload required by the planner UI."""

    model_config = ConfigDict(frozen=True)

    lesson_modes: list[LessonModePreset] = Field(default_factory=list)
    feature_flags: dict[str, bool] = Field(default_factory=dict)


DEFAULT_LESSON_MODE_ID = "group_work"


def get_default_lesson_mode_id() -> str:
    """Return the hidden default lesson mode for fundamentals-first flows."""

    if is_valid_lesson_mode_id(lesson_mode_id=DEFAULT_LESSON_MODE_ID):
        return DEFAULT_LESSON_MODE_ID
    return LESSON_MODE_PRESETS[0].id


class Student(BaseModel):
    """Represent a student in a roster."""

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
    """Represent a seat in a room template."""

    model_config = ConfigDict(frozen=True)

    id: str
    x: int
    y: int
    zone: str | None = None


class RoomFixtureType(StrEnum):
    """Enumerate supported decorative/layout room fixtures."""

    WHITEBOARD = "whiteboard"
    TEACHER_DESK = "teacher_desk"
    WINDOW = "window"
    DOOR = "door"


class RoomFixture(BaseModel):
    """Represent a visual classroom fixture placed on the room canvas."""

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
    """Represent a stable draft-scoped group bucket."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    name: str
    sort_order: int


class GroupAssignment(BaseModel):
    """Represent assignment of a student to a specific group."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    group_id: str


class SeatAssignment(BaseModel):
    """Represent assignment of a student to a specific seat."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    seat_id: str


class StudentPlanningMeta(BaseModel):
    """Represent draft-scoped teacher-only planning metadata for a student."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id: str
    teacher_proximity: int = 0
    independent_focus_support: int = 0
    stability_preference: int = 0
    preferred_zone: str | None = None
    avoid_zone: str | None = None
    notes: str | None = None


class PairConstraintKind(StrEnum):
    """Enumerate supported pairwise planning relationships."""

    KEEP_APART = "keep_apart"
    PREFER_TOGETHER = "prefer_together"
    TEMPORARY_CONFLICT = "temporary_conflict"
    STABLE_PAIR = "stable_pair"


class PairConstraint(BaseModel):
    """Represent a draft-scoped pairwise constraint between two students."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    student_id_a: str
    student_id_b: str
    kind: PairConstraintKind
    strength: int = 1

    @model_validator(mode="after")
    def normalize_student_order(self) -> "PairConstraint":
        """Sort pair ids to keep persistence and comparisons stable."""

        if self.student_id_a <= self.student_id_b:
            return self
        return self.model_copy(
            update={
                "student_id_a": self.student_id_b,
                "student_id_b": self.student_id_a,
            }
        )


class PlanningProfileKind(StrEnum):
    """Enumerate supported planning emphasis profiles."""

    FOCUS_FIRST = "focus_first"
    BALANCE_FIRST = "balance_first"
    ROTATION_FIRST = "rotation_first"


class PlanningProfile(BaseModel):
    """Represent draft-scoped suggestion weighting inputs."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    profile_kind: PlanningProfileKind = PlanningProfileKind.BALANCE_FIRST
    enable_student_meta: bool = True
    enable_pair_constraints: bool = True
    enable_zone_preferences: bool = True
    enable_history_rules: bool = False
    teacher_proximity_weight: int = 1
    focus_support_weight: int = 1
    stability_weight: int = 1
    balance_weight: int = 1
    rotation_weight: int = 1


def default_planning_profile() -> PlanningProfile:
    """Return the default planning profile used for new drafts."""

    return PlanningProfile()


class SuggestionEngineMetadata(BaseModel):
    """Represent provenance for a generated or applied suggestion."""

    model_config = ConfigDict(frozen=True)

    suggestion_id: str
    profile_kind: PlanningProfileKind
    generated_at: datetime
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    explanation_bullets: list[str] = Field(default_factory=list)


class PlanDraftStatus(StrEnum):
    """Enumerate mutable draft lifecycle states."""

    ACTIVE = "active"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class PlanDraft(BaseModel):
    """Represent the mutable root draft record."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str
    status: PlanDraftStatus = PlanDraftStatus.ACTIVE
    revision: int = 0
    engine_metadata: SuggestionEngineMetadata | None = None
    last_opened_at: datetime
    created_at: datetime
    updated_at: datetime


class DraftWorkspace(BaseModel):
    """Represent the full draft-scoped planning workspace."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    student_planning_meta: list[StudentPlanningMeta] = Field(default_factory=list)
    pair_constraints: list[PairConstraint] = Field(default_factory=list)
    planning_profile: PlanningProfile = Field(default_factory=default_planning_profile)


class ClassroomPlannerWorkspace(BaseModel):
    """Represent the hydrated planner context returned to the frontend."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    roster: Roster
    template: RoomTemplate
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    student_planning_meta: list[StudentPlanningMeta] = Field(default_factory=list)
    pair_constraints: list[PairConstraint] = Field(default_factory=list)
    planning_profile: PlanningProfile = Field(default_factory=default_planning_profile)


class ResumablePlanDraft(BaseModel):
    """Represent the latest resumable draft shown on the landing page."""

    model_config = ConfigDict(frozen=True)

    draft: PlanDraft
    roster_name: str
    template_name: str


class ValidationSeverity(StrEnum):
    """Enumerate severity levels for validation findings."""

    HARD = "hard"
    SOFT = "soft"


class ValidationFinding(BaseModel):
    """Represent one normalized planner validation result."""

    model_config = ConfigDict(frozen=True)

    severity: ValidationSeverity
    code: str
    subject_ref: str | None = None
    message: str
    explanation: str


class ValidationResult(BaseModel):
    """Represent the authoritative backend validation response."""

    model_config = ConfigDict(frozen=True)

    findings: list[ValidationFinding] = Field(default_factory=list)

    @property
    def has_hard_violations(self) -> bool:
        """Return whether any hard validation finding exists."""

        return any(finding.severity == ValidationSeverity.HARD for finding in self.findings)


class SuggestionPlan(BaseModel):
    """Represent one explainable suggestion returned by the backend."""

    model_config = ConfigDict(frozen=True)

    suggestion_id: str
    label: str
    profile_kind: PlanningProfileKind
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    findings: list[ValidationFinding] = Field(default_factory=list)
    explanation_bullets: list[str] = Field(default_factory=list)
    engine_metadata: SuggestionEngineMetadata


class SuggestionList(BaseModel):
    """Represent a batch of suggestions for the planner."""

    model_config = ConfigDict(frozen=True)

    suggestions: list[SuggestionPlan] = Field(default_factory=list)


class ArrangementSnapshot(BaseModel):
    """Represent an immutable finalized classroom arrangement snapshot."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    source_draft_id: UUID
    lesson_mode_id: str
    snapshot_schema_version: int = 1
    payload: dict[str, object]
    created_at: datetime
