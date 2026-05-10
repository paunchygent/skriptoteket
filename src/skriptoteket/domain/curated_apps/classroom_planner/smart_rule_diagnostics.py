"""Solver-owned smart-rule diagnostics for Klassrumskartan.

Purpose:
    Convert the current seating assignment into stable rule-status categories
    that classroom-map markers can render without reimplementing solver
    semantics in the frontend.

Relationships:
    - Reuses seat topology and seat-support context from the smart-seating
      domain.
    - Returned additively by authenticated and public Smart seating handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Literal

from skriptoteket.domain.curated_apps.classroom_planner.fixed_seating import (
    fixed_seat_rules_for_template,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_support_context import (
    SeatingContext,
    SeatSupportContext,
    build_seat_support_context,
    near_teacher_band,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatPairTopology,
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)

RuleDiagnosticKind = Literal["fixed_seat", "near_teacher", "keep_near", "keep_apart"]
RuleDiagnosticStatus = Literal["pending", "satisfied", "degraded", "failed"]


@dataclass(frozen=True)
class SmartRuleDiagnostic:
    """Represent one display-safe solver-owned smart-rule diagnostic."""

    rule_id: str | None
    rule_kind: RuleDiagnosticKind
    status: RuleDiagnosticStatus
    student_ids: tuple[str, ...]
    seat_ids: tuple[str, ...]
    reason_code: str
    relation_mode: str | None = None
    seating_context: SeatingContext | None = None
    message_key: str | None = None
    freshness_key: str | None = None

    def with_freshness_key(self, freshness_key: str) -> "SmartRuleDiagnostic":
        """Return this diagnostic bound to one solver-input freshness key."""

        return SmartRuleDiagnostic(
            rule_id=self.rule_id,
            rule_kind=self.rule_kind,
            status=self.status,
            student_ids=self.student_ids,
            seat_ids=self.seat_ids,
            reason_code=self.reason_code,
            relation_mode=self.relation_mode,
            seating_context=self.seating_context,
            message_key=self.message_key,
            freshness_key=freshness_key,
        )


@dataclass(frozen=True)
class _DiagnosticContext:
    topology: SeatTopology
    support_context: SeatSupportContext
    valid_student_ids: set[str]
    valid_seat_ids: set[str]
    seat_id_by_student_id: dict[str, str]
    student_id_by_seat_id: dict[str, str]


def build_smart_rule_diagnostics(
    *,
    roster: Roster,
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    seat_assignments: list[SeatAssignment],
) -> tuple[SmartRuleDiagnostic, ...]:
    """Build solver-owned diagnostics for the current seating state."""

    anchor = infer_teaching_anchor(template=template)
    topology = build_seat_topology(
        seats=list(template.seats),
        anchor=anchor,
        fixtures=list(template.fixtures),
    )
    support_context = build_seat_support_context(
        seats=list(template.seats),
        fixtures=list(template.fixtures),
        anchor=anchor,
    )
    context = _DiagnosticContext(
        topology=topology,
        support_context=support_context,
        valid_student_ids={student.id for student in roster.students},
        valid_seat_ids={seat.id for seat in template.seats},
        seat_id_by_student_id={
            assignment.student_id: assignment.seat_id for assignment in seat_assignments
        },
        student_id_by_seat_id={
            assignment.seat_id: assignment.student_id for assignment in seat_assignments
        },
    )
    diagnostics: list[SmartRuleDiagnostic] = []
    diagnostics.extend(
        _fixed_seat_diagnostics(
            template=template,
            smart_rules=smart_rules,
            context=context,
        )
    )
    diagnostics.extend(_near_teacher_diagnostics(smart_rules=smart_rules, context=context))
    diagnostics.extend(_relationship_diagnostics(smart_rules=smart_rules, context=context))
    return tuple(diagnostics)


def _fixed_seat_diagnostics(
    *,
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    context: _DiagnosticContext,
) -> list[SmartRuleDiagnostic]:
    diagnostics: list[SmartRuleDiagnostic] = []
    for rule in fixed_seat_rules_for_template(
        smart_rules=smart_rules,
        template_id=template.id,
    ):
        status: RuleDiagnosticStatus
        reason_code: str
        if (
            rule.student_id not in context.valid_student_ids
            or rule.seat_id not in context.valid_seat_ids
        ):
            status = "failed"
            reason_code = "fixed_seat_invalid_reference"
        elif context.seat_id_by_student_id.get(rule.student_id) == rule.seat_id:
            status = "satisfied"
            reason_code = "fixed_seat_exact"
        elif context.student_id_by_seat_id.get(rule.seat_id):
            status = "failed"
            reason_code = "fixed_seat_wrong_student_in_seat"
        elif context.seat_id_by_student_id.get(rule.student_id):
            status = "failed"
            reason_code = "fixed_seat_student_elsewhere"
        else:
            status = "pending"
            reason_code = "fixed_seat_waiting_for_assignment"
        diagnostics.append(
            SmartRuleDiagnostic(
                rule_id=rule.id,
                rule_kind="fixed_seat",
                status=status,
                student_ids=(rule.student_id,),
                seat_ids=(rule.seat_id,),
                reason_code=reason_code,
            )
        )
    return diagnostics


def _near_teacher_diagnostics(
    *, smart_rules: RosterSmartRules, context: _DiagnosticContext
) -> list[SmartRuleDiagnostic]:
    diagnostics: list[SmartRuleDiagnostic] = []
    for preference in smart_rules.seating_preferences:
        if not preference.near_teacher:
            continue
        seat_id = context.seat_id_by_student_id.get(preference.student_id)
        if preference.student_id not in context.valid_student_ids:
            diagnostics.append(_near_teacher_invalid(preference.student_id))
            continue
        if seat_id is None:
            diagnostics.append(
                SmartRuleDiagnostic(
                    rule_id=f"near_teacher:{preference.student_id}",
                    rule_kind="near_teacher",
                    status="pending",
                    student_ids=(preference.student_id,),
                    seat_ids=(),
                    reason_code="near_teacher_waiting_for_assignment",
                )
            )
            continue
        band = near_teacher_band(
            seat_id=seat_id,
            topology=context.topology,
            support_context=context.support_context,
        )
        diagnostics.append(
            SmartRuleDiagnostic(
                rule_id=f"near_teacher:{preference.student_id}",
                rule_kind="near_teacher",
                status=_near_teacher_status(band),
                student_ids=(preference.student_id,),
                seat_ids=(seat_id,),
                reason_code=_near_teacher_reason_code(
                    seat_id=seat_id,
                    band=band,
                    context=context,
                ),
                seating_context=context.support_context.seat_context(seat_id),
            )
        )
    return diagnostics


def _relationship_diagnostics(
    *, smart_rules: RosterSmartRules, context: _DiagnosticContext
) -> list[SmartRuleDiagnostic]:
    diagnostics: list[SmartRuleDiagnostic] = []
    for rule in smart_rules.relationship_rules:
        student_ids = tuple(rule.student_ids)
        if any(student_id not in context.valid_student_ids for student_id in student_ids):
            diagnostics.append(
                SmartRuleDiagnostic(
                    rule_id=rule.id,
                    rule_kind=_relationship_rule_kind(rule.kind),
                    status="failed",
                    student_ids=student_ids,
                    seat_ids=(),
                    reason_code="relationship_invalid_reference",
                )
            )
            continue
        seat_ids = tuple(
            context.seat_id_by_student_id[student_id]
            for student_id in student_ids
            if student_id in context.seat_id_by_student_id
        )
        if len(seat_ids) < len(student_ids):
            diagnostics.append(
                SmartRuleDiagnostic(
                    rule_id=rule.id,
                    rule_kind=_relationship_rule_kind(rule.kind),
                    status="pending",
                    student_ids=student_ids,
                    seat_ids=seat_ids,
                    reason_code="relationship_waiting_for_assignment",
                )
            )
            continue
        if rule.kind is RelationshipKind.KEEP_NEAR:
            diagnostics.append(
                _keep_near_diagnostic(
                    rule_id=rule.id,
                    student_ids=student_ids,
                    seat_ids=seat_ids,
                    context=context,
                )
            )
        else:
            diagnostics.append(
                _keep_apart_diagnostic(
                    rule_id=rule.id,
                    student_ids=student_ids,
                    seat_ids=seat_ids,
                    context=context,
                )
            )
    return diagnostics


def _keep_near_diagnostic(
    *,
    rule_id: str,
    student_ids: tuple[str, ...],
    seat_ids: tuple[str, ...],
    context: _DiagnosticContext,
) -> SmartRuleDiagnostic:
    if len(student_ids) > 6:
        return SmartRuleDiagnostic(
            rule_id=rule_id,
            rule_kind="keep_near",
            status="degraded",
            student_ids=student_ids,
            seat_ids=seat_ids,
            reason_code="keep_near_group_too_large_for_precise_diagnostic",
            seating_context="unknown",
            message_key="keep_near_group_too_large",
        )
    if len(student_ids) == 2:
        pair = context.topology.pair(seat_ids[0], seat_ids[1])
        seating_context = context.support_context.pair_context(
            left_seat_id=seat_ids[0],
            right_seat_id=seat_ids[1],
            pair=pair,
        )
        status, reason_code = _keep_near_pair_status(
            pair=pair,
            seating_context=seating_context,
        )
        return SmartRuleDiagnostic(
            rule_id=rule_id,
            rule_kind="keep_near",
            status=status,
            student_ids=student_ids,
            seat_ids=seat_ids,
            reason_code=reason_code,
            relation_mode=pair.keep_near_relation_mode or "none",
            seating_context=seating_context,
        )
    return _keep_near_group_diagnostic(
        rule_id=rule_id,
        student_ids=student_ids,
        seat_ids=seat_ids,
        context=context,
    )


def _keep_near_pair_status(
    *, pair: SeatPairTopology, seating_context: SeatingContext
) -> tuple[RuleDiagnosticStatus, str]:
    relation_mode = pair.keep_near_relation_mode
    if seating_context == "shared_table":
        if relation_mode in {"adjacent-row", "adjacent-column"}:
            return "satisfied", "keep_near_shared_table_adjacent"
        if relation_mode in {"diagonal-block", "one-step-row", "one-step-column"}:
            return "degraded", "keep_near_shared_table_compact_tradeoff"
        return "failed", "keep_near_not_close"
    if seating_context in {"bench_row", "row_layout"}:
        if relation_mode == "adjacent-row":
            return "satisfied", "keep_near_row_adjacent"
        if relation_mode == "adjacent-column":
            return "degraded", "keep_near_row_non_adjacent_tradeoff"
        return "failed", "keep_near_row_not_close"
    if pair.orthogonally_adjacent:
        return "degraded", "keep_near_unknown_adjacent_tradeoff"
    return "failed", "keep_near_not_close"


def _keep_near_group_diagnostic(
    *,
    rule_id: str,
    student_ids: tuple[str, ...],
    seat_ids: tuple[str, ...],
    context: _DiagnosticContext,
) -> SmartRuleDiagnostic:
    group_context = _group_seating_context(seat_ids=seat_ids, context=context)
    status: RuleDiagnosticStatus
    if group_context == "shared_table":
        status, reason_code = "satisfied", "keep_near_group_same_table"
    elif _has_table_split(seat_ids=seat_ids, context=context):
        status, reason_code = "failed", "keep_near_group_split_tables"
    elif _all_same_local_zone(seat_ids=seat_ids, context=context):
        status, reason_code = (
            ("satisfied", "keep_near_group_compact_cluster")
            if len(student_ids) <= 4
            else ("degraded", "keep_near_group_large_compact_tradeoff")
        )
    else:
        status, reason_code = "failed", "keep_near_group_split_zones"
    return SmartRuleDiagnostic(
        rule_id=rule_id,
        rule_kind="keep_near",
        status=status,
        student_ids=student_ids,
        seat_ids=seat_ids,
        reason_code=reason_code,
        seating_context=group_context,
    )


def _keep_apart_diagnostic(
    *,
    rule_id: str,
    student_ids: tuple[str, ...],
    seat_ids: tuple[str, ...],
    context: _DiagnosticContext,
) -> SmartRuleDiagnostic:
    status: RuleDiagnosticStatus = "satisfied"
    reason_code = "keep_apart_separated"
    for left_seat_id, right_seat_id in combinations(seat_ids, 2):
        pair = context.topology.pair(left_seat_id, right_seat_id)
        if pair.orthogonally_adjacent or pair.diagonal_neighbor:
            status, reason_code = "failed", "keep_apart_immediate_contact"
            break
        if pair.same_block or pair.same_local_zone:
            status, reason_code = "degraded", "keep_apart_same_zone_tradeoff"
    return SmartRuleDiagnostic(
        rule_id=rule_id,
        rule_kind="keep_apart",
        status=status,
        student_ids=student_ids,
        seat_ids=seat_ids,
        reason_code=reason_code,
    )


def _group_seating_context(
    *, seat_ids: tuple[str, ...], context: _DiagnosticContext
) -> SeatingContext:
    group_keys = {context.support_context.group_key_by_seat_id.get(seat_id) for seat_id in seat_ids}
    if len(group_keys) == 1:
        group_key = next(iter(group_keys))
        if group_key is not None:
            return context.support_context.context_by_group_key.get(group_key, "unknown")
    seat_contexts = {context.support_context.seat_context(seat_id) for seat_id in seat_ids}
    if seat_contexts == {"row_layout"}:
        return "row_layout"
    if _all_same_local_zone(seat_ids=seat_ids, context=context):
        return "local_cluster"
    return "unknown"


def _has_table_split(*, seat_ids: tuple[str, ...], context: _DiagnosticContext) -> bool:
    seat_contexts = {context.support_context.seat_context(seat_id) for seat_id in seat_ids}
    if "shared_table" in seat_contexts and seat_contexts != {"shared_table"}:
        return True
    table_group_keys = {
        context.support_context.group_key_by_seat_id.get(seat_id)
        for seat_id in seat_ids
        if context.support_context.seat_context(seat_id) == "shared_table"
    }
    return len(table_group_keys) > 1


def _all_same_local_zone(*, seat_ids: tuple[str, ...], context: _DiagnosticContext) -> bool:
    return len({context.topology.local_zone_id_by_seat[seat_id] for seat_id in seat_ids}) == 1


def _near_teacher_invalid(student_id: str) -> SmartRuleDiagnostic:
    return SmartRuleDiagnostic(
        rule_id=f"near_teacher:{student_id}",
        rule_kind="near_teacher",
        status="failed",
        student_ids=(student_id,),
        seat_ids=(),
        reason_code="near_teacher_invalid_reference",
    )


def _relationship_rule_kind(kind: RelationshipKind) -> RuleDiagnosticKind:
    return "keep_near" if kind is RelationshipKind.KEEP_NEAR else "keep_apart"


def _near_teacher_status(
    band: Literal["desired", "degraded", "failed"],
) -> RuleDiagnosticStatus:
    if band == "desired":
        return "satisfied"
    if band == "degraded":
        return "degraded"
    return "failed"


def _near_teacher_reason_code(
    *,
    seat_id: str,
    band: Literal["desired", "degraded", "failed"],
    context: _DiagnosticContext,
) -> str:
    seat_context = context.support_context.seat_context(seat_id)
    if band == "desired":
        return (
            "near_teacher_table_closest_groups"
            if seat_context == "shared_table"
            else "near_teacher_row_first_rank"
        )
    if band == "degraded":
        return (
            "near_teacher_table_compromise_group"
            if seat_context == "shared_table"
            else "near_teacher_row_front_compromise"
        )
    return "near_teacher_too_far"
