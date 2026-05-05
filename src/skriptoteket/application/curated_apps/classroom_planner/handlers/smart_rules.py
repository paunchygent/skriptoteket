"""Roster-owned smart-rule handlers for the classroom planner.

This module owns the class-global smart-rule set that belongs to one roster.
It keeps smart-rule validation and persistence separate from draft-local
arrangement patches so multiple drafts for the same class reuse the same rules.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipRule,
    RoomTemplate,
    RosterSmartRules,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.protocols.classroom_planner import (
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .smart_rule_validation import normalize_seating_preferences, validate_roster_smart_rules


class GetRosterSmartRulesHandler:
    """Load roster-owned smart rules for one class."""

    def __init__(
        self,
        rosters: RosterRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> None:
        self._rosters = rosters
        self._smart_rules = smart_rules

    async def handle(self, *, roster_id: UUID, owner_user_id: UUID) -> RosterSmartRules:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        return await self._smart_rules.get_by_roster_id(roster_id=roster_id)


class PatchRosterSmartRulesHandler:
    """Patch roster-owned smart rules independently of draft autosave."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._templates = templates
        self._smart_rules = smart_rules

    async def handle(
        self,
        *,
        roster_id: UUID,
        owner_user_id: UUID,
        expected_revision: int,
        seating_preferences: list[StudentSeatingPreference],
        relationship_rules: list[RelationshipRule],
        fixed_seat_rules: list[FixedSeatRule],
    ) -> RosterSmartRules:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        seating_preferences = normalize_seating_preferences(seating_preferences)
        if expected_revision < 0:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Roster smart-rule revision must be zero or greater.",
            )

        validate_roster_smart_rules(
            roster=roster,
            seating_preferences=seating_preferences,
            relationship_rules=relationship_rules,
            fixed_seat_rules=fixed_seat_rules,
            templates_by_id=await self._load_owned_templates_by_id(
                owner_user_id=owner_user_id,
                fixed_seat_rules=fixed_seat_rules,
            ),
        )
        rules = RosterSmartRules(
            roster_id=roster_id,
            revision=expected_revision,
            seating_preferences=seating_preferences,
            relationship_rules=relationship_rules,
            fixed_seat_rules=fixed_seat_rules,
        )
        async with self._uow:
            return await self._smart_rules.save(
                rules=rules,
                expected_revision=expected_revision,
            )

    async def _load_owned_templates_by_id(
        self,
        *,
        owner_user_id: UUID,
        fixed_seat_rules: list[FixedSeatRule],
    ) -> dict[str, RoomTemplate]:
        template_ids = {rule.template_id for rule in fixed_seat_rules}
        templates_by_id: dict[str, RoomTemplate] = {}
        for template_id in template_ids:
            template = await self._templates.get_by_id(template_id=template_id)
            if template is not None and template.owner_user_id == owner_user_id:
                templates_by_id[str(template_id)] = template
        return templates_by_id
