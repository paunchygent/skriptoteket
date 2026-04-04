"""Asset-resolution collaborators for Klassrumskartan guest upgrades.

This module owns the non-destructive import policy for reusable rosters,
room templates, and roster-global smart rules so the main guest-upgrade
handler can stay focused on orchestration flow.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeReceiptItem,
    ClassroomPlannerGuestUpgradeRequest,
    GuestUpgradeRosterPayload,
    GuestUpgradeSmartRuleSetPayload,
    GuestUpgradeTemplatePayload,
    build_server_roster_fingerprint,
    build_server_smart_rule_fingerprint,
    build_server_template_fingerprint,
    build_smart_rule_fingerprint_relationship_rule,
    build_smart_rule_fingerprint_seating_preference,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipRule,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Student,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.classroom_planner import (
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol

from .guest_upgrade_support import MappedRoster, MappedTemplate, build_preview_uuid
from .smart_rule_validation import normalize_seating_preferences, validate_roster_smart_rules


class GuestUpgradeAssetImporter:
    """Resolve reusable assets for one authenticated guest-upgrade request."""

    def __init__(
        self,
        *,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._rosters = rosters
        self._templates = templates
        self._smart_rules = smart_rules
        self._clock = clock
        self._id_generator = id_generator

    async def import_assets(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
    ) -> tuple[dict[str, MappedRoster], dict[str, MappedTemplate]]:
        """Resolve rosters, templates, and smart rules for one guest snapshot."""

        existing_rosters = await self._rosters.list_by_owner(owner_user_id=owner_user_id)
        existing_templates = await self._templates.list_by_owner(owner_user_id=owner_user_id)
        roster_cache: dict[str, MappedRoster] = {}
        template_cache: dict[str, MappedTemplate] = {}

        for guest_roster in snapshot.rosters:
            mapped_roster = await self._map_roster(
                owner_user_id=owner_user_id,
                request=request,
                snapshot=snapshot,
                receipt=receipt,
                existing_rosters=existing_rosters,
                guest_roster=guest_roster,
            )
            roster_cache[guest_roster.local_id] = mapped_roster
            if mapped_roster.was_created:
                existing_rosters.append(mapped_roster.roster)

        for guest_template in snapshot.templates:
            mapped_template = await self._map_template(
                owner_user_id=owner_user_id,
                request=request,
                snapshot=snapshot,
                receipt=receipt,
                existing_templates=existing_templates,
                guest_template=guest_template,
            )
            template_cache[guest_template.local_id] = mapped_template
            if mapped_template.was_created:
                existing_templates.append(mapped_template.template)

        for smart_rule_set in snapshot.smart_rule_sets:
            await self._process_smart_rules(
                receipt=receipt,
                request=request,
                roster_cache=roster_cache,
                smart_rule_set=smart_rule_set,
            )

        return roster_cache, template_cache

    async def _map_roster(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        existing_rosters: list[Roster],
        guest_roster: GuestUpgradeRosterPayload,
    ) -> MappedRoster:
        target = next(
            (
                roster
                for roster in existing_rosters
                if build_server_roster_fingerprint(guest_roster)
                == build_server_roster_fingerprint(
                    guest_roster.model_copy(
                        update={
                            "students": [
                                student.model_copy(update={"local_id": roster_student.id})
                                for student, roster_student in zip(
                                    guest_roster.students,
                                    roster.students,
                                    strict=False,
                                )
                            ]
                        }
                    )
                )
                and [student.display_name for student in roster.students]
                == [student.display_name for student in guest_roster.students]
            ),
            None,
        )
        if target is not None:
            receipt.reused.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="roster",
                    local_id=guest_roster.local_id,
                    target_id=str(target.id),
                    target_name=target.name,
                )
            )
            return MappedRoster(
                roster=target,
                student_id_map={
                    guest_student.local_id: roster_student.id
                    for guest_student, roster_student in zip(
                        guest_roster.students,
                        target.students,
                        strict=True,
                    )
                },
                was_created=False,
            )

        now = self._clock.now()
        roster = Roster(
            id=(
                self._id_generator.new_uuid()
                if request.mode == "commit"
                else build_preview_uuid(
                    snapshot_id=snapshot.snapshot_id,
                    entity_type="roster",
                    local_id=guest_roster.local_id,
                )
            ),
            owner_user_id=owner_user_id,
            name=guest_roster.name,
            students=[
                Student(id=student.local_id, display_name=student.display_name)
                for student in guest_roster.students
            ],
            created_at=now,
            updated_at=now,
        )
        if request.mode == "commit":
            await self._rosters.save(roster=roster)
        receipt.created.append(
            ClassroomPlannerGuestUpgradeReceiptItem(
                entity_type="roster",
                local_id=guest_roster.local_id,
                target_id=str(roster.id) if request.mode == "commit" else None,
                target_name=roster.name,
            )
        )
        return MappedRoster(
            roster=roster,
            student_id_map={
                student.local_id: student.local_id for student in guest_roster.students
            },
            was_created=True,
        )

    async def _map_template(
        self,
        *,
        owner_user_id: UUID,
        request: ClassroomPlannerGuestUpgradeRequest,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        existing_templates: list[RoomTemplate],
        guest_template: GuestUpgradeTemplatePayload,
    ) -> MappedTemplate:
        target = next(
            (
                template
                for template in existing_templates
                if build_server_template_fingerprint(guest_template)
                == build_server_template_fingerprint(
                    guest_template.model_copy(
                        update={
                            "seats": [
                                seat.model_copy(update={"id": template_seat.id})
                                for seat, template_seat in zip(
                                    sorted(
                                        guest_template.seats,
                                        key=lambda seat: (seat.x, seat.y, seat.zone or ""),
                                    ),
                                    sorted(
                                        template.seats,
                                        key=lambda seat: (seat.x, seat.y, seat.zone or ""),
                                    ),
                                    strict=False,
                                )
                            ]
                        }
                    )
                )
            ),
            None,
        )
        if target is not None:
            coordinate_map = {
                f"{seat.x}:{seat.y}:{seat.zone or ''}": seat.id for seat in target.seats
            }
            receipt.reused.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="template",
                    local_id=guest_template.local_id,
                    target_id=str(target.id),
                    target_name=target.name,
                )
            )
            return MappedTemplate(
                template=target,
                seat_id_map={
                    seat.id: coordinate_map[f"{seat.x}:{seat.y}:{seat.zone or ''}"]
                    for seat in guest_template.seats
                },
                was_created=False,
            )

        now = self._clock.now()
        template = RoomTemplate(
            id=(
                self._id_generator.new_uuid()
                if request.mode == "commit"
                else build_preview_uuid(
                    snapshot_id=snapshot.snapshot_id,
                    entity_type="template",
                    local_id=guest_template.local_id,
                )
            ),
            owner_user_id=owner_user_id,
            name=guest_template.name,
            grid_cols=guest_template.grid_cols or 14,
            grid_rows=guest_template.grid_rows or 9,
            seats=guest_template.seats,
            fixtures=guest_template.fixtures,
            created_at=now,
            updated_at=now,
        )
        if request.mode == "commit":
            await self._templates.save(template=template)
        receipt.created.append(
            ClassroomPlannerGuestUpgradeReceiptItem(
                entity_type="template",
                local_id=guest_template.local_id,
                target_id=str(template.id) if request.mode == "commit" else None,
                target_name=template.name,
            )
        )
        return MappedTemplate(
            template=template,
            seat_id_map={seat.id: seat.id for seat in guest_template.seats},
            was_created=True,
        )

    async def _process_smart_rules(
        self,
        *,
        receipt: ClassroomPlannerGuestUpgradeReceipt,
        request: ClassroomPlannerGuestUpgradeRequest,
        roster_cache: dict[str, MappedRoster],
        smart_rule_set: GuestUpgradeSmartRuleSetPayload,
    ) -> None:
        mapped_roster = roster_cache.get(smart_rule_set.roster_local_id)
        if mapped_roster is None:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="smart_rule_set",
                    local_id=smart_rule_set.roster_local_id,
                    message="Smart rules references an unmapped roster.",
                )
            )
            return

        missing_preference_students = sorted(
            {
                preference.student_id
                for preference in smart_rule_set.seating_preferences
                if preference.student_id not in mapped_roster.student_id_map
            }
        )
        if missing_preference_students:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="smart_rule_set",
                    local_id=smart_rule_set.roster_local_id,
                    target_id=str(mapped_roster.roster.id),
                    target_name=mapped_roster.roster.name,
                    message=(
                        "Smart rules reference guest students that could not be mapped "
                        "to the authenticated roster."
                    ),
                )
            )
            return

        invalid_relationship_rule_ids: list[str] = []
        relationship_rules: list[RelationshipRule] = []
        for rule in smart_rule_set.relationship_rules:
            mapped_student_ids = [
                mapped_roster.student_id_map[student_id]
                for student_id in rule.student_ids
                if student_id in mapped_roster.student_id_map
            ]
            if len(mapped_student_ids) != len(rule.student_ids):
                invalid_relationship_rule_ids.append(rule.id)
                continue
            if len(mapped_student_ids) < 2 or len(set(mapped_student_ids)) < 2:
                invalid_relationship_rule_ids.append(rule.id)
                continue
            relationship_rules.append(
                RelationshipRule(
                    id=rule.id,
                    kind=rule.kind,
                    student_ids=mapped_student_ids,
                )
            )
        if invalid_relationship_rule_ids:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="smart_rule_set",
                    local_id=smart_rule_set.roster_local_id,
                    target_id=str(mapped_roster.roster.id),
                    target_name=mapped_roster.roster.name,
                    message=(
                        "Smart rules contain invalid relationship rules after student "
                        "mapping and were left unchanged."
                    ),
                )
            )
            return

        seating_preferences = normalize_seating_preferences(
            [
                StudentSeatingPreference(
                    student_id=mapped_roster.student_id_map[preference.student_id],
                    near_teacher=preference.near_teacher,
                )
                for preference in smart_rule_set.seating_preferences
            ]
        )
        try:
            validate_roster_smart_rules(
                roster=mapped_roster.roster,
                seating_preferences=seating_preferences,
                relationship_rules=relationship_rules,
            )
        except DomainError as error:
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="smart_rule_set",
                    local_id=smart_rule_set.roster_local_id,
                    target_id=str(mapped_roster.roster.id),
                    target_name=mapped_roster.roster.name,
                    message=error.message,
                )
            )
            return
        current_rules = await self._smart_rules.get_by_roster_id(roster_id=mapped_roster.roster.id)
        target_fingerprint = build_server_smart_rule_fingerprint(
            seating_preferences=[
                build_smart_rule_fingerprint_seating_preference(entry)
                for entry in seating_preferences
            ],
            relationship_rules=[
                build_smart_rule_fingerprint_relationship_rule(rule) for rule in relationship_rules
            ],
        )
        current_fingerprint = build_server_smart_rule_fingerprint(
            seating_preferences=[
                build_smart_rule_fingerprint_seating_preference(entry)
                for entry in current_rules.seating_preferences
            ],
            relationship_rules=[
                build_smart_rule_fingerprint_relationship_rule(rule)
                for rule in current_rules.relationship_rules
            ],
        )
        if target_fingerprint == current_fingerprint:
            receipt.reused.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="smart_rule_set",
                    local_id=smart_rule_set.roster_local_id,
                    target_id=str(mapped_roster.roster.id),
                    target_name=mapped_roster.roster.name,
                )
            )
            return
        if (
            current_rules.revision != 0
            or current_rules.seating_preferences
            or current_rules.relationship_rules
        ):
            receipt.conflicted.append(
                ClassroomPlannerGuestUpgradeReceiptItem(
                    entity_type="smart_rule_set",
                    local_id=smart_rule_set.roster_local_id,
                    target_id=str(mapped_roster.roster.id),
                    target_name=mapped_roster.roster.name,
                    message="Existing authenticated smart rules differ and were left unchanged.",
                )
            )
            return

        if request.mode == "commit":
            await self._smart_rules.save(
                rules=RosterSmartRules(
                    roster_id=mapped_roster.roster.id,
                    revision=current_rules.revision,
                    seating_preferences=seating_preferences,
                    relationship_rules=relationship_rules,
                ),
                expected_revision=current_rules.revision,
            )
        receipt.created.append(
            ClassroomPlannerGuestUpgradeReceiptItem(
                entity_type="smart_rule_set",
                local_id=smart_rule_set.roster_local_id,
                target_id=str(mapped_roster.roster.id) if request.mode == "commit" else None,
                target_name=mapped_roster.roster.name,
            )
        )
