"""Support helpers for Klassrumskartan public Smart application handlers.

Purpose:
    Keep the anonymous Smart handlers focused on solver orchestration by
    centralizing guest-snapshot materialization, invariant checks, and public
    workspace serialization.

Relationships:
    - Reuses the approved browser-owned guest snapshot payloads from
      `guest_upgrade_contracts.py`.
    - Reuses smart-rule validation from `smart_rule_validation.py`.
    - Consumed by the public Smart grouping and seating handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
    GuestUpgradeDraftPayload,
    GuestUpgradeRosterPayload,
    GuestUpgradeSmartRuleSetPayload,
    GuestUpgradeTemplatePayload,
)
from skriptoteket.application.curated_apps.classroom_planner.public_smart_run_contracts import (
    PublicDraftHistoryStatusDto,
    PublicDraftWorkspaceResponse,
    PublicPlanDraftDto,
    PublicRoomFixtureDto,
    PublicRoomTemplateDto,
    PublicRosterDto,
    PublicSeatDto,
    PublicSmartGroupingBlockedResponse,
    PublicSmartSeatingBlockedResponse,
    PublicStudentDto,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftHistoryStatus,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import validation_error

from .smart_rule_validation import normalize_seating_preferences, validate_roster_smart_rules

PUBLIC_SMART_RUN_MAX_STUDENTS = 80
PUBLIC_SMART_RUN_MAX_GROUPS = 12
PUBLIC_SMART_RUN_MAX_SEATS = 160
PUBLIC_SMART_RUN_MAX_FIXTURES = 64
PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULES = 32
PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULE_STUDENTS = 8
PUBLIC_SMART_RUN_GUEST_OWNER_ID = uuid5(
    NAMESPACE_URL,
    "skriptoteket:classroom-planner:public-smart:guest-owner",
)


@dataclass(frozen=True, slots=True)
class MaterializedPublicSmartWorkspace:
    """Bundle one guest draft snapshot with domain-ready Smart inputs."""

    draft_payload: GuestUpgradeDraftPayload
    roster_payload: GuestUpgradeRosterPayload
    template_payload: GuestUpgradeTemplatePayload | None
    roster: Roster
    template: RoomTemplate | None
    smart_rules: RosterSmartRules
    workspace: DraftWorkspace


def materialize_public_smart_workspace(
    *,
    snapshot: ClassroomPlannerGuestSnapshotPayload,
    draft_kind: PlanDraftKind,
    now: datetime,
) -> MaterializedPublicSmartWorkspace:
    """Materialize one browser-owned guest draft into domain-ready Smart inputs."""

    draft_payload = _resolve_draft(snapshot=snapshot, draft_kind=draft_kind)
    roster_payload = _resolve_roster(
        snapshot=snapshot, roster_local_id=draft_payload.roster_local_id
    )
    template_payload = _resolve_template(
        snapshot=snapshot,
        template_local_id=draft_payload.template_local_id,
    )

    _validate_roster_payload(roster_payload)
    _validate_template_payload(template_payload)
    _validate_draft_payload(
        draft_payload=draft_payload,
        roster_payload=roster_payload,
        template_payload=template_payload,
    )

    roster = _build_roster(roster_payload=roster_payload, now=now)
    template = _build_template(template_payload=template_payload, now=now)
    smart_rule_payload = _resolve_smart_rule_set(
        snapshot=snapshot,
        roster_local_id=draft_payload.roster_local_id,
    )
    smart_rules = _build_smart_rules(
        roster=roster,
        smart_rule_payload=smart_rule_payload,
    )
    workspace = _build_workspace(
        draft_payload=draft_payload,
        roster=roster,
        template=template,
        now=now,
    )
    _validate_workspace_assignments(
        draft_payload=draft_payload,
        roster_payload=roster_payload,
        template_payload=template_payload,
    )
    return MaterializedPublicSmartWorkspace(
        draft_payload=draft_payload,
        roster_payload=roster_payload,
        template_payload=template_payload,
        roster=roster,
        template=template,
        smart_rules=smart_rules,
        workspace=workspace,
    )


def build_public_classroom_planner_workspace(
    *,
    materialized: MaterializedPublicSmartWorkspace,
) -> ClassroomPlannerWorkspace:
    """Hydrate the canonical planner workspace for public export preparation."""

    return ClassroomPlannerWorkspace(
        draft=materialized.workspace.draft,
        roster=materialized.roster,
        template=materialized.template,
        groups=list(materialized.workspace.groups),
        group_assignments=list(materialized.workspace.group_assignments),
        seat_assignments=list(materialized.workspace.seat_assignments),
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def build_public_workspace_response(
    *,
    draft_payload: GuestUpgradeDraftPayload,
    roster_payload: GuestUpgradeRosterPayload,
    template_payload: GuestUpgradeTemplatePayload | None,
    groups: list[DraftGroup],
    group_assignments: list[GroupAssignment],
    seat_assignments: list[SeatAssignment],
) -> PublicDraftWorkspaceResponse:
    """Serialize one browser-owned Smart workspace response with local ids."""

    return PublicDraftWorkspaceResponse(
        draft=PublicPlanDraftDto(
            id=draft_payload.local_id,
            roster_id=draft_payload.roster_local_id,
            draft_kind=draft_payload.draft_kind,
            template_id=draft_payload.template_local_id,
            task_entry_classroom_selection_mode=draft_payload.task_entry_classroom_selection_mode,
            smart_enabled=draft_payload.smart_enabled,
            use_history=draft_payload.use_history,
            grouping_seating_distance_enabled=draft_payload.grouping_seating_distance_enabled,
            status="active",
            revision=draft_payload.revision,
            last_opened_at=draft_payload.last_opened_at,
        ),
        roster=PublicRosterDto(
            id=roster_payload.local_id,
            name=roster_payload.name,
            students=[
                PublicStudentDto(id=student.local_id, display_name=student.display_name)
                for student in roster_payload.students
            ],
        ),
        template=(
            PublicRoomTemplateDto(
                id=template_payload.local_id,
                name=template_payload.name,
                grid_cols=template_payload.grid_cols,
                grid_rows=template_payload.grid_rows,
                seats=[
                    PublicSeatDto(
                        id=seat.id,
                        x=seat.x,
                        y=seat.y,
                        zone=seat.zone,
                    )
                    for seat in template_payload.seats
                ],
                fixtures=[
                    PublicRoomFixtureDto(
                        id=fixture.id,
                        type=fixture.type.value,
                        x=fixture.x,
                        y=fixture.y,
                        width=fixture.width,
                        height=fixture.height,
                        label=fixture.label,
                    )
                    for fixture in template_payload.fixtures
                ],
            )
            if template_payload is not None
            else None
        ),
        groups=list(groups),
        group_assignments=list(group_assignments),
        seat_assignments=list(seat_assignments),
        history_status=PublicDraftHistoryStatusDto(can_undo=False, can_redo=False),
    )


def build_history_blocked_grouping_response(
    *,
    message: str,
    used_live_seating: bool,
) -> PublicSmartGroupingBlockedResponse:
    """Return one explicit blocked public grouping response."""

    return PublicSmartGroupingBlockedResponse(
        status="blocked",
        reason="no_history",
        workspace=None,
        used_history=False,
        used_live_seating=used_live_seating,
        message=message,
    )


def build_history_blocked_seating_response(*, message: str) -> PublicSmartSeatingBlockedResponse:
    """Return one explicit blocked public seating response."""

    return PublicSmartSeatingBlockedResponse(
        status="blocked",
        reason="no_history",
        workspace=None,
        used_history=False,
        message=message,
    )


def _resolve_draft(
    *,
    snapshot: ClassroomPlannerGuestSnapshotPayload,
    draft_kind: PlanDraftKind,
) -> GuestUpgradeDraftPayload:
    draft_payload = (
        snapshot.grouping_draft if draft_kind is PlanDraftKind.GROUPING else snapshot.seating_draft
    )
    if draft_payload is None:
        raise validation_error(f"Public Smart {draft_kind.value} requires an active guest draft.")
    if draft_payload.draft_kind is not draft_kind:
        raise validation_error(f"Public Smart {draft_kind.value} requires a matching guest draft.")
    return draft_payload


def _resolve_roster(
    *,
    snapshot: ClassroomPlannerGuestSnapshotPayload,
    roster_local_id: str,
) -> GuestUpgradeRosterPayload:
    for roster in snapshot.rosters:
        if roster.local_id == roster_local_id:
            return roster
    raise validation_error("Public Smart payload references an unknown guest roster.")


def _resolve_template(
    *,
    snapshot: ClassroomPlannerGuestSnapshotPayload,
    template_local_id: str | None,
) -> GuestUpgradeTemplatePayload | None:
    if template_local_id is None:
        return None
    for template in snapshot.templates:
        if template.local_id == template_local_id:
            return template
    raise validation_error("Public Smart payload references an unknown guest classroom.")


def _resolve_smart_rule_set(
    *,
    snapshot: ClassroomPlannerGuestSnapshotPayload,
    roster_local_id: str,
) -> GuestUpgradeSmartRuleSetPayload | None:
    for rule_set in snapshot.smart_rule_sets:
        if rule_set.roster_local_id == roster_local_id:
            return rule_set
    return None


def _validate_roster_payload(roster_payload: GuestUpgradeRosterPayload) -> None:
    if len(roster_payload.students) > PUBLIC_SMART_RUN_MAX_STUDENTS:
        raise validation_error("Public Smart payload exceeds the supported class size.")
    _ensure_unique(
        [student.local_id for student in roster_payload.students],
        label="Public Smart student ids",
    )


def _validate_template_payload(template_payload: GuestUpgradeTemplatePayload | None) -> None:
    if template_payload is None:
        return
    if len(template_payload.seats) > PUBLIC_SMART_RUN_MAX_SEATS:
        raise validation_error("Public Smart payload exceeds the supported seat count.")
    if len(template_payload.fixtures) > PUBLIC_SMART_RUN_MAX_FIXTURES:
        raise validation_error("Public Smart payload exceeds the supported fixture count.")
    _ensure_unique(
        [seat.id for seat in template_payload.seats],
        label="Public Smart seat ids",
    )
    _ensure_unique(
        [fixture.id for fixture in template_payload.fixtures],
        label="Public Smart fixture ids",
    )


def _validate_draft_payload(
    *,
    draft_payload: GuestUpgradeDraftPayload,
    roster_payload: GuestUpgradeRosterPayload,
    template_payload: GuestUpgradeTemplatePayload | None,
) -> None:
    if draft_payload.use_history:
        raise validation_error("Use history is account-only in guest Smart.")
    if draft_payload.draft_kind is PlanDraftKind.SEATING and template_payload is None:
        raise validation_error("Public Smart seating requires a guest classroom.")
    if len(draft_payload.groups) > PUBLIC_SMART_RUN_MAX_GROUPS:
        raise validation_error("Public Smart payload exceeds the supported group count.")
    _ensure_unique(
        [group.id for group in draft_payload.groups],
        label="Public Smart group ids",
    )
    if len(roster_payload.students) > 0 and len(draft_payload.group_assignments) > len(
        roster_payload.students
    ):
        raise validation_error("Public Smart grouping assignments cannot exceed the roster size.")
    if template_payload is not None and len(draft_payload.seat_assignments) > len(
        template_payload.seats
    ):
        raise validation_error("Public Smart seating assignments cannot exceed the seat count.")


def _validate_workspace_assignments(
    *,
    draft_payload: GuestUpgradeDraftPayload,
    roster_payload: GuestUpgradeRosterPayload,
    template_payload: GuestUpgradeTemplatePayload | None,
) -> None:
    student_ids = {student.local_id for student in roster_payload.students}
    group_ids = {group.id for group in draft_payload.groups}
    seat_ids = (
        {seat.id for seat in template_payload.seats} if template_payload is not None else set()
    )

    _ensure_unique(
        [assignment.student_id for assignment in draft_payload.group_assignments],
        label="Public Smart grouping assignment student ids",
    )
    for assignment in draft_payload.group_assignments:
        if assignment.student_id not in student_ids:
            raise validation_error(
                "Public Smart grouping assignments must reference roster students."
            )
        if assignment.group_id not in group_ids:
            raise validation_error("Public Smart grouping assignments must reference draft groups.")

    _ensure_unique(
        [assignment.student_id for assignment in draft_payload.seat_assignments],
        label="Public Smart seating assignment student ids",
    )
    _ensure_unique(
        [assignment.seat_id for assignment in draft_payload.seat_assignments],
        label="Public Smart seating assignment seat ids",
    )
    for seat_assignment in draft_payload.seat_assignments:
        if seat_assignment.student_id not in student_ids:
            raise validation_error(
                "Public Smart seating assignments must reference roster students."
            )
        if seat_assignment.seat_id not in seat_ids:
            raise validation_error(
                "Public Smart seating assignments must reference template seats."
            )


def _build_roster(
    *,
    roster_payload: GuestUpgradeRosterPayload,
    now: datetime,
) -> Roster:
    return Roster(
        id=_guest_uuid(f"roster:{roster_payload.local_id}"),
        owner_user_id=PUBLIC_SMART_RUN_GUEST_OWNER_ID,
        name=roster_payload.name,
        students=[
            Student(id=student.local_id, display_name=student.display_name)
            for student in roster_payload.students
        ],
        created_at=now,
        updated_at=now,
    )


def _build_template(
    *,
    template_payload: GuestUpgradeTemplatePayload | None,
    now: datetime,
) -> RoomTemplate | None:
    if template_payload is None:
        return None
    return RoomTemplate(
        id=_guest_uuid(f"template:{template_payload.local_id}"),
        owner_user_id=PUBLIC_SMART_RUN_GUEST_OWNER_ID,
        name=template_payload.name,
        grid_cols=template_payload.grid_cols or 1,
        grid_rows=template_payload.grid_rows or 1,
        seats=list(template_payload.seats),
        fixtures=list(template_payload.fixtures),
        created_at=now,
        updated_at=now,
    )


def _build_smart_rules(
    *,
    roster: Roster,
    smart_rule_payload: GuestUpgradeSmartRuleSetPayload | None,
) -> RosterSmartRules:
    if smart_rule_payload is None:
        return RosterSmartRules(
            roster_id=roster.id,
            revision=0,
            seating_preferences=[],
            relationship_rules=[],
        )

    if len(smart_rule_payload.relationship_rules) > PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULES:
        raise validation_error(
            "Public Smart payload exceeds the supported relationship-rule count."
        )
    for rule in smart_rule_payload.relationship_rules:
        if len(rule.student_ids) > PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULE_STUDENTS:
            raise validation_error("Public Smart relationship rules exceed the supported size.")

    seating_preferences = normalize_seating_preferences(
        list(smart_rule_payload.seating_preferences)
    )
    relationship_rules = list(smart_rule_payload.relationship_rules)
    validate_roster_smart_rules(
        roster=roster,
        seating_preferences=seating_preferences,
        relationship_rules=relationship_rules,
    )
    return RosterSmartRules(
        roster_id=roster.id,
        revision=smart_rule_payload.revision,
        seating_preferences=seating_preferences,
        relationship_rules=relationship_rules,
    )


def _build_workspace(
    *,
    draft_payload: GuestUpgradeDraftPayload,
    roster: Roster,
    template: RoomTemplate | None,
    now: datetime,
) -> DraftWorkspace:
    return DraftWorkspace(
        draft=PlanDraft(
            id=_guest_uuid(f"draft:{draft_payload.local_id}"),
            owner_user_id=PUBLIC_SMART_RUN_GUEST_OWNER_ID,
            roster_id=roster.id,
            draft_kind=draft_payload.draft_kind,
            template_id=template.id if template is not None else None,
            task_entry_classroom_selection_mode=draft_payload.task_entry_classroom_selection_mode,
            smart_enabled=draft_payload.smart_enabled,
            use_history=False,
            grouping_seating_distance_enabled=draft_payload.grouping_seating_distance_enabled,
            status=PlanDraftStatus.ACTIVE,
            revision=draft_payload.revision,
            last_opened_at=_parse_iso_datetime(draft_payload.last_opened_at, fallback=now),
            created_at=now,
            updated_at=now,
        ),
        groups=list(draft_payload.groups),
        group_assignments=list(draft_payload.group_assignments),
        seat_assignments=list(draft_payload.seat_assignments),
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _parse_iso_datetime(value: str, *, fallback: datetime) -> datetime:
    normalized = value.strip()
    if normalized == "":
        return fallback
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return fallback
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _guest_uuid(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"skriptoteket:classroom-planner:public-smart:{key}")


def _ensure_unique(values: list[str], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise validation_error(f"{label} must be unique.")
