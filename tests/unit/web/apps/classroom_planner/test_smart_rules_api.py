"""API tests for roster-owned classroom planner smart rules."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    GetRosterSmartRulesHandler,
    PatchRosterSmartRulesHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RelationshipRule,
    RosterSmartRules,
    StudentSeatingPreference,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner_smart_rules as api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""

    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
def test_update_roster_smart_rules_request_rejects_legacy_support_seat_payload() -> None:
    with pytest.raises(ValidationError):
        api.UpdateRosterSmartRulesRequest.model_validate(
            {
                "expected_revision": 0,
                "seating_preferences": [
                    {
                        "student_id": "s1",
                        "support_seat": True,
                    }
                ],
            }
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_roster_smart_rules_calls_handler() -> None:
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetRosterSmartRulesHandler)
    roster_id = uuid4()
    handler.handle.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=3,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=["s1", "s2"],
            )
        ],
    )

    result = await _unwrap_dishka(api.get_roster_smart_rules)(
        roster_id=roster_id,
        handler=handler,
        user=user,
    )

    assert result.roster_id == roster_id
    assert result.revision == 3
    assert result.seating_preferences == [
        api.StudentSeatingPreferenceDto(student_id="s1", near_teacher=True)
    ]
    assert result.relationship_rules == [
        api.RelationshipRuleDto(
            id="rule-1",
            kind=RelationshipKind.KEEP_NEAR.value,
            student_ids=["s1", "s2"],
        )
    ]
    handler.handle.assert_awaited_once_with(roster_id=roster_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_roster_smart_rules_calls_handler() -> None:
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=PatchRosterSmartRulesHandler)
    roster_id = uuid4()
    request = api.UpdateRosterSmartRulesRequest(
        expected_revision=3,
        seating_preferences=[api.StudentSeatingPreferenceDto(student_id="s1", near_teacher=True)],
        relationship_rules=[
            api.RelationshipRuleDto(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART.value,
                student_ids=["s1", "s2", "s3"],
            )
        ],
    )
    handler.handle.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=4,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["s1", "s2", "s3"],
            )
        ],
    )

    result = await _unwrap_dishka(api.update_roster_smart_rules)(
        roster_id=roster_id,
        request=request,
        handler=handler,
        user=user,
    )

    assert result.roster_id == roster_id
    assert result.revision == 4
    handler.handle.assert_awaited_once_with(
        roster_id=roster_id,
        owner_user_id=user.id,
        expected_revision=3,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["s1", "s2", "s3"],
            )
        ],
    )
