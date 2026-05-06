"""Application contracts for Klassrumskartan authenticated guest upgrades.

Purpose:
    Define the typed request and receipt models plus deterministic
    fingerprinting helpers used by the authenticated guest-upgrade
    orchestration boundary.

Relationships:
    - Consumed by `handlers.guest_upgrade`.
    - Reused by the authenticated guest-upgrade API route for request and
      response serialization.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.application.curated_apps.classroom_planner.guest_smart_rule_fingerprints import (
    build_server_smart_rule_fingerprint,
    build_smart_rule_fingerprint_fixed_seat_rule,
    build_smart_rule_fingerprint_relationship_rule,
    build_smart_rule_fingerprint_seating_preference,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    DraftGroup,
    FixedSeatRule,
    GroupAssignment,
    PlanDraftKind,
    RelationshipRule,
    RoomFixture,
    Seat,
    SeatAssignment,
    StudentSeatingPreference,
)

SNAPSHOT_PROFILE = "public_browser_workspace_with_upgrade"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_payload(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value).encode('utf-8')).hexdigest()}"


class GuestUpgradeStudentPayload(BaseModel):
    """Describe one guest-stored student inside a browser-owned roster."""

    model_config = ConfigDict(frozen=True)

    local_id: str
    display_name: str


class GuestUpgradeRosterPayload(BaseModel):
    """Describe one guest-stored roster candidate."""

    model_config = ConfigDict(frozen=True)

    local_id: str
    name: str
    students: list[GuestUpgradeStudentPayload]
    fingerprint: str


class GuestUpgradeTemplatePayload(BaseModel):
    """Describe one guest-stored room template candidate."""

    model_config = ConfigDict(frozen=True)

    local_id: str
    name: str
    grid_cols: int | None = None
    grid_rows: int | None = None
    seats: list[Seat]
    fixtures: list[RoomFixture] = Field(default_factory=list)
    fingerprint: str


class GuestUpgradeSmartRuleSetPayload(BaseModel):
    """Describe one guest-stored roster-global smart-rule set."""

    model_config = ConfigDict(frozen=True)

    roster_local_id: str
    revision: int
    seating_preferences: list[StudentSeatingPreference] = Field(default_factory=list)
    relationship_rules: list[RelationshipRule] = Field(default_factory=list)
    fixed_seat_rules: list[FixedSeatRule] = Field(default_factory=list)
    fingerprint: str


class GuestUpgradeDraftPayload(BaseModel):
    """Describe one guest-stored draft that may become imported history."""

    model_config = ConfigDict(frozen=True)

    local_id: str
    draft_kind: PlanDraftKind
    roster_local_id: str
    template_local_id: str | None = None
    task_entry_classroom_selection_mode: ClassroomSelectionMode
    smart_enabled: bool = True
    use_history: bool = False
    grouping_seating_distance_enabled: bool = False
    revision: int
    last_opened_at: str
    groups: list[DraftGroup] = Field(default_factory=list)
    group_assignments: list[GroupAssignment] = Field(default_factory=list)
    seat_assignments: list[SeatAssignment] = Field(default_factory=list)
    fingerprint: str


class GuestUpgradeCheckpointPayload(BaseModel):
    """Describe one guest-stored export checkpoint candidate."""

    model_config = ConfigDict(frozen=True)

    local_id: str
    draft_kind: PlanDraftKind
    created_at: str
    label: str | None = None
    source: Literal["export"] = "export"
    template_local_id: str | None = None
    group_assignments: list[GroupAssignment] | None = None
    seat_assignments: list[SeatAssignment] | None = None
    fingerprint: str

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "GuestUpgradeCheckpointPayload":
        """Require the canonical checkpoint payload fields for the declared draft kind."""

        if self.draft_kind is PlanDraftKind.GROUPING and self.group_assignments is None:
            raise ValueError("Grouping checkpoints must include group_assignments.")
        if self.draft_kind is PlanDraftKind.SEATING:
            if self.template_local_id is None:
                raise ValueError("Seating checkpoints must include template_local_id.")
            if self.seat_assignments is None:
                raise ValueError("Seating checkpoints must include seat_assignments.")
        return self


class GuestUpgradeUiStatePayload(BaseModel):
    """Describe guest-only UI state carried inside the browser snapshot."""

    model_config = ConfigDict(frozen=True)

    selected_roster_local_id: str | None = None
    selected_template_local_id: str | None = None
    current_screen: str
    planner_initial_view: str
    dismissed_grouping_draft_local_id: str | None = None
    dismissed_seating_draft_local_id: str | None = None
    fingerprint: str


class ClassroomPlannerGuestSnapshotPayload(BaseModel):
    """Describe the full guest snapshot submitted to the upgrade boundary."""

    model_config = ConfigDict(frozen=True)

    schema_version: int
    profile: Literal["public_browser_workspace_with_upgrade"]
    snapshot_id: str
    snapshot_content_hash: str
    created_at: str
    updated_at: str
    expires_at: str
    rosters: list[GuestUpgradeRosterPayload] = Field(default_factory=list)
    templates: list[GuestUpgradeTemplatePayload] = Field(default_factory=list)
    smart_rule_sets: list[GuestUpgradeSmartRuleSetPayload] = Field(default_factory=list)
    grouping_draft: GuestUpgradeDraftPayload | None = None
    seating_draft: GuestUpgradeDraftPayload | None = None
    checkpoint_descriptors: list[GuestUpgradeCheckpointPayload] = Field(default_factory=list)
    ui_state: GuestUpgradeUiStatePayload


class ClassroomPlannerGuestUpgradeRequest(BaseModel):
    """Describe one preview or commit call to the guest-upgrade boundary."""

    model_config = ConfigDict(frozen=True)

    mode: Literal["preview", "commit"]
    snapshot: ClassroomPlannerGuestSnapshotPayload


class ClassroomPlannerGuestUpgradeReceiptItem(BaseModel):
    """Describe one entity-level guest-upgrade receipt line."""

    model_config = ConfigDict(frozen=True)

    entity_type: Literal["roster", "template", "smart_rule_set", "draft", "checkpoint"]
    local_id: str
    draft_kind: PlanDraftKind | None = None
    target_id: str | None = None
    target_name: str | None = None
    message: str | None = None


class ClassroomPlannerGuestUpgradeReceipt(BaseModel):
    """Describe the preview or commit outcome for one guest snapshot."""

    model_config = ConfigDict(frozen=True)

    mode: Literal["preview", "commit"]
    snapshot_id: str
    schema_version: int
    submitted_snapshot_content_hash: str
    server_snapshot_content_hash: str
    created: list[ClassroomPlannerGuestUpgradeReceiptItem] = Field(default_factory=list)
    reused: list[ClassroomPlannerGuestUpgradeReceiptItem] = Field(default_factory=list)
    skipped: list[ClassroomPlannerGuestUpgradeReceiptItem] = Field(default_factory=list)
    conflicted: list[ClassroomPlannerGuestUpgradeReceiptItem] = Field(default_factory=list)


def build_server_roster_fingerprint(payload: GuestUpgradeRosterPayload) -> str:
    """Hash a guest roster by portable teacher-facing content."""

    return _sha256_payload(
        {
            "name": payload.name,
            "students": [{"display_name": student.display_name} for student in payload.students],
        }
    )


def build_server_template_fingerprint(payload: GuestUpgradeTemplatePayload) -> str:
    """Hash a guest room template by portable room geometry."""

    return _sha256_payload(
        {
            "name": payload.name,
            "grid_cols": payload.grid_cols,
            "grid_rows": payload.grid_rows,
            "seats": [
                {
                    "x": seat.x,
                    "y": seat.y,
                    "zone": seat.zone,
                }
                for seat in sorted(
                    payload.seats,
                    key=lambda seat: (seat.x, seat.y, seat.zone or ""),
                )
            ],
            "fixtures": [
                {
                    "type": fixture.type.value,
                    "x": fixture.x,
                    "y": fixture.y,
                    "width": fixture.width,
                    "height": fixture.height,
                    "label": fixture.label,
                }
                for fixture in sorted(
                    payload.fixtures,
                    key=lambda fixture: (
                        fixture.type.value,
                        fixture.x,
                        fixture.y,
                        fixture.width,
                        fixture.height,
                        fixture.label or "",
                    ),
                )
            ],
        }
    )


def build_server_draft_fingerprint(payload: GuestUpgradeDraftPayload) -> str:
    """Hash a guest draft by its portable arrangement payload."""

    ordered_groups = sorted(payload.groups, key=lambda group: (group.sort_order, group.id))
    ordered_group_assignments = sorted(
        payload.group_assignments,
        key=lambda assignment: (assignment.student_id, assignment.group_id),
    )
    ordered_seat_assignments = sorted(
        payload.seat_assignments,
        key=lambda assignment: (assignment.student_id, assignment.seat_id),
    )
    return _sha256_payload(
        {
            "draft_kind": payload.draft_kind.value,
            "roster_local_id": payload.roster_local_id,
            "template_local_id": payload.template_local_id,
            "task_entry_classroom_selection_mode": (
                payload.task_entry_classroom_selection_mode.value
            ),
            "smart_enabled": payload.smart_enabled,
            "use_history": payload.use_history,
            "grouping_seating_distance_enabled": payload.grouping_seating_distance_enabled,
            "revision": payload.revision,
            "groups": [group.model_dump(mode="json") for group in ordered_groups],
            "group_assignments": [
                assignment.model_dump(mode="json") for assignment in ordered_group_assignments
            ],
            "seat_assignments": [
                assignment.model_dump(mode="json") for assignment in ordered_seat_assignments
            ],
        }
    )


def build_server_checkpoint_fingerprint(payload: GuestUpgradeCheckpointPayload) -> str:
    """Hash a guest checkpoint by its portable exported arrangement payload."""

    return _sha256_payload(
        {
            "draft_kind": payload.draft_kind.value,
            "template_local_id": payload.template_local_id,
            "group_assignments": (
                [
                    assignment.model_dump(mode="json")
                    for assignment in sorted(
                        payload.group_assignments,
                        key=lambda assignment: (assignment.student_id, assignment.group_id),
                    )
                ]
                if payload.group_assignments is not None
                else None
            ),
            "seat_assignments": (
                [
                    assignment.model_dump(mode="json")
                    for assignment in sorted(
                        payload.seat_assignments,
                        key=lambda assignment: (assignment.student_id, assignment.seat_id),
                    )
                ]
                if payload.seat_assignments is not None
                else None
            ),
        }
    )


def build_guest_import_identity(
    *,
    snapshot_id: str,
    server_snapshot_content_hash: str,
    draft_payload: GuestUpgradeDraftPayload,
) -> str:
    """Build one durable imported-draft identity from server-owned facts."""

    return _sha256_payload(
        {
            "snapshot_id": snapshot_id,
            "server_snapshot_content_hash": server_snapshot_content_hash,
            "draft_kind": draft_payload.draft_kind.value,
            "draft_local_id": draft_payload.local_id,
            "draft_fingerprint": build_server_draft_fingerprint(draft_payload),
            "task_entry_classroom_selection_mode": (
                draft_payload.task_entry_classroom_selection_mode.value
            ),
        }
    )


def recompute_server_snapshot(
    snapshot: ClassroomPlannerGuestSnapshotPayload,
) -> ClassroomPlannerGuestSnapshotPayload:
    """Return the guest snapshot with server-owned hashes and fingerprints."""

    roster_payloads = [
        roster.model_copy(update={"fingerprint": build_server_roster_fingerprint(roster)})
        for roster in snapshot.rosters
    ]
    template_payloads = [
        template.model_copy(update={"fingerprint": build_server_template_fingerprint(template)})
        for template in snapshot.templates
    ]
    smart_rule_payloads = [
        smart_rules.model_copy(
            update={
                "fingerprint": build_server_smart_rule_fingerprint(
                    seating_preferences=[
                        build_smart_rule_fingerprint_seating_preference(preference)
                        for preference in smart_rules.seating_preferences
                    ],
                    relationship_rules=[
                        build_smart_rule_fingerprint_relationship_rule(rule)
                        for rule in smart_rules.relationship_rules
                    ],
                    fixed_seat_rules=[
                        build_smart_rule_fingerprint_fixed_seat_rule(rule)
                        for rule in smart_rules.fixed_seat_rules
                    ],
                )
            }
        )
        for smart_rules in snapshot.smart_rule_sets
    ]
    grouping_draft = (
        snapshot.grouping_draft.model_copy(
            update={"fingerprint": build_server_draft_fingerprint(snapshot.grouping_draft)}
        )
        if snapshot.grouping_draft is not None
        else None
    )
    seating_draft = (
        snapshot.seating_draft.model_copy(
            update={"fingerprint": build_server_draft_fingerprint(snapshot.seating_draft)}
        )
        if snapshot.seating_draft is not None
        else None
    )
    checkpoint_payloads = [
        checkpoint.model_copy(
            update={"fingerprint": build_server_checkpoint_fingerprint(checkpoint)}
        )
        for checkpoint in snapshot.checkpoint_descriptors
    ]
    ui_state = snapshot.ui_state.model_copy(
        update={
            "fingerprint": _sha256_payload(
                {
                    "selected_roster_local_id": snapshot.ui_state.selected_roster_local_id,
                    "selected_template_local_id": snapshot.ui_state.selected_template_local_id,
                    "current_screen": snapshot.ui_state.current_screen,
                    "planner_initial_view": snapshot.ui_state.planner_initial_view,
                    "dismissed_grouping_draft_local_id": (
                        snapshot.ui_state.dismissed_grouping_draft_local_id
                    ),
                    "dismissed_seating_draft_local_id": (
                        snapshot.ui_state.dismissed_seating_draft_local_id
                    ),
                }
            )
        }
    )

    payload_without_hash = {
        "schema_version": snapshot.schema_version,
        "profile": snapshot.profile,
        "snapshot_id": snapshot.snapshot_id,
        "created_at": snapshot.created_at,
        "updated_at": snapshot.updated_at,
        "expires_at": snapshot.expires_at,
        "rosters": [roster.model_dump(mode="json") for roster in roster_payloads],
        "templates": [template.model_dump(mode="json") for template in template_payloads],
        "smart_rule_sets": [rules.model_dump(mode="json") for rules in smart_rule_payloads],
        "grouping_draft": grouping_draft.model_dump(mode="json") if grouping_draft else None,
        "seating_draft": seating_draft.model_dump(mode="json") if seating_draft else None,
        "checkpoint_descriptors": [
            checkpoint.model_dump(mode="json") for checkpoint in checkpoint_payloads
        ],
        "ui_state": ui_state.model_dump(mode="json"),
    }

    return snapshot.model_copy(
        update={
            "snapshot_content_hash": _sha256_payload(payload_without_hash),
            "rosters": roster_payloads,
            "templates": template_payloads,
            "smart_rule_sets": smart_rule_payloads,
            "grouping_draft": grouping_draft,
            "seating_draft": seating_draft,
            "checkpoint_descriptors": checkpoint_payloads,
            "ui_state": ui_state,
        }
    )
