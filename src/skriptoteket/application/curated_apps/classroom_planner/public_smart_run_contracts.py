"""Application contracts for Klassrumskartan public Smart helper routes.

Purpose:
    Define the typed request and response models used by the anonymous
    browser-owned Smart helper seams so the web layer can stay transport-thin.

Relationships:
    - Reuses the approved browser-owned guest snapshot payload from
      `guest_upgrade_contracts.py`.
    - Returned by the public Smart application handlers and serialized by the
      dedicated `/api/v1/public/apps/.../smart-run` routes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    DraftGroup,
    GroupAssignment,
    PlanDraftKind,
    RelationshipKind,
    SeatAssignment,
)

from .smart_rule_diagnostic_contracts import SmartRuleDiagnosticDto


class PublicSmartRunRequest(BaseModel):
    """Describe one stateless public Smart helper request."""

    model_config = ConfigDict(frozen=True)

    expected_revision: int = Field(ge=0)
    snapshot: ClassroomPlannerGuestSnapshotPayload


class PublicStudentDto(BaseModel):
    """Serialize one browser-owned student inside a public Smart workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    display_name: str


class PublicRosterDto(BaseModel):
    """Serialize one browser-owned roster inside a public Smart workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    students: list[PublicStudentDto]


class PublicRoomFixtureDto(BaseModel):
    """Serialize one browser-owned room fixture inside a public Smart workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: str
    x: int
    y: int
    width: int
    height: int
    label: str | None = None


class PublicSeatDto(BaseModel):
    """Serialize one browser-owned seat inside a public Smart workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    x: int
    y: int
    zone: str | None = None


class PublicRoomTemplateDto(BaseModel):
    """Serialize one browser-owned room template inside a public Smart workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    grid_cols: int | None = None
    grid_rows: int | None = None
    seats: list[PublicSeatDto]
    fixtures: list[PublicRoomFixtureDto] = Field(default_factory=list)


class PublicPlanDraftDto(BaseModel):
    """Serialize the mutable browser-owned draft root for public Smart routes."""

    model_config = ConfigDict(frozen=True)

    id: str
    roster_id: str
    draft_kind: PlanDraftKind
    template_id: str | None = None
    task_entry_classroom_selection_mode: ClassroomSelectionMode
    smart_enabled: bool = True
    use_history: bool = False
    grouping_seating_distance_enabled: bool = False
    status: Literal["active"] = "active"
    revision: int
    last_opened_at: str


class PublicDraftHistoryStatusDto(BaseModel):
    """Serialize the local-only undo/redo availability for one public workspace."""

    model_config = ConfigDict(frozen=True)

    can_undo: bool
    can_redo: bool


class PublicDraftWorkspaceResponse(BaseModel):
    """Serialize one browser-owned workspace returned by a public Smart helper."""

    model_config = ConfigDict(frozen=True)

    draft: PublicPlanDraftDto
    roster: PublicRosterDto
    template: PublicRoomTemplateDto | None = None
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    history_status: PublicDraftHistoryStatusDto


class PublicSmartGroupingAppliedResponse(BaseModel):
    """Serialize one applied public guest Smart grouping result."""

    model_config = ConfigDict(frozen=True)

    status: Literal["applied"]
    workspace: PublicDraftWorkspaceResponse
    used_history: bool
    used_live_seating: bool
    message: str | None = None


class PublicSmartGroupingBlockedResponse(BaseModel):
    """Serialize one blocked public guest Smart grouping result."""

    model_config = ConfigDict(frozen=True)

    status: Literal["blocked"]
    reason: Literal["no_history"]
    workspace: None = None
    used_history: bool
    used_live_seating: bool
    message: str


class PublicSmartSeatingAppliedResponse(BaseModel):
    """Serialize one applied public guest Smart seating result."""

    model_config = ConfigDict(frozen=True)

    status: Literal["applied"]
    workspace: PublicDraftWorkspaceResponse
    used_history: bool
    message: str | None = None
    rule_diagnostics: list[SmartRuleDiagnosticDto] = Field(default_factory=list)


class PublicSmartSeatingBlockedResponse(BaseModel):
    """Serialize one blocked public guest Smart seating result."""

    model_config = ConfigDict(frozen=True)

    status: Literal["blocked"]
    reason: Literal["no_history"]
    workspace: None = None
    used_history: bool
    message: str


class PublicStudentSeatingPreferenceDto(BaseModel):
    """Describe one browser-owned seating preference in a Smart helper request."""

    model_config = ConfigDict(frozen=True)

    student_id: str
    near_teacher: bool = False


class PublicRelationshipRuleDto(BaseModel):
    """Describe one browser-owned relationship rule in a Smart helper request."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: RelationshipKind
    student_ids: list[str]
