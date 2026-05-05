"""API contracts for roster-owned Klassrumskartan smart rules.

Purpose:
    Describe the additive smart-rule payloads used by the authenticated
    `Regler` API, including near-teacher preferences, relationship clusters,
    and hard fixed-seat placements.

Relationships:
    - Imported by the smart-rule router for request and response models.
    - Shares the same identifier uniqueness convention as the planner router.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StudentSeatingPreferenceDto(BaseModel):
    """Serialize per-student seating-only preferences."""

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")
    student_id: str
    near_teacher: bool = False


class RelationshipRuleDto(BaseModel):
    """Serialize a student relationship constraint."""

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")
    id: str
    kind: str
    student_ids: list[str]


class FixedSeatRuleDto(BaseModel):
    """Serialize one hard student-to-seat placement for a classroom."""

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")
    id: str
    template_id: UUID
    student_id: str
    seat_id: str
