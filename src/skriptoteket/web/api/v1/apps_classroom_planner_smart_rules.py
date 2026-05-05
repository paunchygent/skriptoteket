"""Roster-owned smart-rule endpoints for the Classroom Planner curated app.
This router exposes the class-global smart-rule contract separately from the
draft workspace so rule authoring no longer depends on draft autosave or the
draft PATCH/read boundary.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.application.curated_apps.classroom_planner import (
    GetRosterSmartRulesHandler,
    PatchRosterSmartRulesHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipRule,
    RosterSmartRules,
    StudentSeatingPreference,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1.apps_classroom_planner import _assert_unique
from skriptoteket.web.api.v1.apps_classroom_planner_smart_rule_contracts import (
    FixedSeatRuleDto,
    RelationshipRuleDto,
    StudentSeatingPreferenceDto,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio", tags=["apps", "classroom-planner"]
)


class RosterSmartRulesResponse(BaseModel):
    """Serialize roster-owned smart rules for one class."""

    model_config = ConfigDict(frozen=True)
    roster_id: UUID
    revision: int
    seating_preferences: list[StudentSeatingPreferenceDto]
    relationship_rules: list[RelationshipRuleDto]
    fixed_seat_rules: list[FixedSeatRuleDto]


class UpdateRosterSmartRulesRequest(BaseModel):
    """Deserialize roster-owned smart-rule updates."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int
    seating_preferences: list[StudentSeatingPreferenceDto] = []
    relationship_rules: list[RelationshipRuleDto] = []
    fixed_seat_rules: list[FixedSeatRuleDto] = []

    @model_validator(mode="after")
    def validate_unique_collections(self) -> "UpdateRosterSmartRulesRequest":
        _assert_unique(
            [pref.student_id for pref in self.seating_preferences],
            label="Seating preference student",
        )
        _assert_unique([rule.id for rule in self.relationship_rules], label="Relationship rule")
        _assert_unique([rule.id for rule in self.fixed_seat_rules], label="Fixed-seat rule")
        return self


def _serialize_roster_smart_rules(rules: RosterSmartRules) -> RosterSmartRulesResponse:
    """Map roster-owned smart rules to the public API response."""
    return RosterSmartRulesResponse(
        roster_id=rules.roster_id,
        revision=rules.revision,
        seating_preferences=[
            StudentSeatingPreferenceDto.model_validate(preference)
            for preference in rules.seating_preferences
        ],
        relationship_rules=[
            RelationshipRuleDto.model_validate(rule) for rule in rules.relationship_rules
        ],
        fixed_seat_rules=[FixedSeatRuleDto.model_validate(rule) for rule in rules.fixed_seat_rules],
    )


@router.get("/rosters/{roster_id}/smart-rules", response_model=RosterSmartRulesResponse)
async def get_roster_smart_rules(
    roster_id: UUID,
    handler: FromDishka[GetRosterSmartRulesHandler],
    user: User = Depends(require_app_user_api),
) -> RosterSmartRulesResponse:
    return _serialize_roster_smart_rules(
        await handler.handle(roster_id=roster_id, owner_user_id=user.id)
    )


@router.patch("/rosters/{roster_id}/smart-rules", response_model=RosterSmartRulesResponse)
async def update_roster_smart_rules(
    roster_id: UUID,
    request: UpdateRosterSmartRulesRequest,
    handler: FromDishka[PatchRosterSmartRulesHandler],
    user: User = Depends(require_app_user_api),
) -> RosterSmartRulesResponse:
    rules = await handler.handle(
        roster_id=roster_id,
        owner_user_id=user.id,
        expected_revision=request.expected_revision,
        seating_preferences=[
            StudentSeatingPreference.model_validate(preference.model_dump())
            for preference in request.seating_preferences
        ],
        relationship_rules=[
            RelationshipRule.model_validate(rule.model_dump())
            for rule in request.relationship_rules
        ],
        fixed_seat_rules=[
            FixedSeatRule.model_validate(rule.model_dump()) for rule in request.fixed_seat_rules
        ],
    )
    return _serialize_roster_smart_rules(rules)
