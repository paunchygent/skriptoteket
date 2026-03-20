"""Domain models for the Classroom Planner curated app (Klassrumskartan)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LessonModePreset(BaseModel):
    """A predefined configuration for a lesson, affecting seating rules and constraints."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str


class ClassroomPlannerBootstrapPayload(BaseModel):
    """The initial state and metadata required to bootstrap the Classroom Planner UI."""

    model_config = ConfigDict(frozen=True)

    lesson_modes: list[LessonModePreset] = Field(default_factory=list)
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class Student(BaseModel):
    """A student in a roster."""

    model_config = ConfigDict(frozen=True)

    id: str
    display_name: str


class Roster(BaseModel):
    """A collection of students (e.g., a class)."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    name: str
    students: list[Student]
    created_at: datetime
    updated_at: datetime


class Seat(BaseModel):
    """A seat in a room template."""

    model_config = ConfigDict(frozen=True)

    id: str
    x: int
    y: int
    zone: str | None = None


class RoomTemplate(BaseModel):
    """A physical room layout with seats."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    name: str
    seats: list[Seat]
    created_at: datetime
    updated_at: datetime


class PlanDraft(BaseModel):
    """An active draft of a seating/grouping plan."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    roster_id: UUID
    template_id: UUID
    lesson_mode_id: str

    # student_id -> group_id
    group_assignments: dict[str, str | None] = Field(default_factory=dict)
    # student_id -> seat_id
    seat_assignments: dict[str, str | None] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime
