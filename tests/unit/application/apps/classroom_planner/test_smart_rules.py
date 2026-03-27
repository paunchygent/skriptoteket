"""Application tests for roster-owned classroom planner smart rules."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner.handlers.smart_rules import (
    GetRosterSmartRulesHandler,
    PatchRosterSmartRulesHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RelationshipRule,
    Roster,
    RosterSmartRules,
    Student,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError


def _build_roster(*, roster_id, owner_user_id) -> Roster:
    now = datetime.now(timezone.utc)
    return Roster(
        id=roster_id,
        owner_user_id=owner_user_id,
        name="SA24D",
        students=[
            Student(id="s1", display_name="Ada"),
            Student(id="s2", display_name="Alan"),
            Student(id="s3", display_name="Barbara"),
        ],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_roster_smart_rules_returns_repo_rules_for_owned_roster() -> None:
    roster_id = uuid4()
    owner_user_id = uuid4()
    rosters = AsyncMock()
    smart_rules = AsyncMock()
    rosters.get_by_id.return_value = _build_roster(roster_id=roster_id, owner_user_id=owner_user_id)
    smart_rules.get_by_roster_id.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=2,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[],
    )
    handler = GetRosterSmartRulesHandler(rosters=rosters, smart_rules=smart_rules)

    result = await handler.handle(roster_id=roster_id, owner_user_id=owner_user_id)

    assert result == RosterSmartRules(
        roster_id=roster_id,
        revision=2,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[],
    )


@pytest.mark.asyncio
async def test_patch_roster_smart_rules_saves_valid_rules_through_uow() -> None:
    roster_id = uuid4()
    owner_user_id = uuid4()
    rosters = AsyncMock()
    smart_rules = AsyncMock()
    uow = AsyncMock()
    rosters.get_by_id.return_value = _build_roster(roster_id=roster_id, owner_user_id=owner_user_id)
    smart_rules.save.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=1,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["s2", "s3"],
            )
        ],
    )
    handler = PatchRosterSmartRulesHandler(uow=uow, rosters=rosters, smart_rules=smart_rules)

    result = await handler.handle(
        roster_id=roster_id,
        owner_user_id=owner_user_id,
        expected_revision=0,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["s2", "s3"],
            )
        ],
    )

    smart_rules.save.assert_awaited_once_with(
        rules=RosterSmartRules(
            roster_id=roster_id,
            revision=0,
            seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
            relationship_rules=[
                RelationshipRule(
                    id="rule-1",
                    kind=RelationshipKind.KEEP_APART,
                    student_ids=["s2", "s3"],
                )
            ],
        ),
        expected_revision=0,
    )
    assert result == RosterSmartRules(
        roster_id=roster_id,
        revision=1,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["s2", "s3"],
            )
        ],
    )
    uow.__aenter__.assert_awaited_once()
    uow.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_roster_smart_rules_rejects_overlapping_relationship_clusters() -> None:
    roster_id = uuid4()
    owner_user_id = uuid4()
    rosters = AsyncMock()
    smart_rules = AsyncMock()
    uow = AsyncMock()
    rosters.get_by_id.return_value = _build_roster(roster_id=roster_id, owner_user_id=owner_user_id)
    handler = PatchRosterSmartRulesHandler(uow=uow, rosters=rosters, smart_rules=smart_rules)

    with pytest.raises(DomainError, match="at most one relationship rule"):
        await handler.handle(
            roster_id=roster_id,
            owner_user_id=owner_user_id,
            expected_revision=0,
            seating_preferences=[],
            relationship_rules=[
                RelationshipRule(
                    id="rule-1",
                    kind=RelationshipKind.KEEP_APART,
                    student_ids=["s1", "s2"],
                ),
                RelationshipRule(
                    id="rule-2",
                    kind=RelationshipKind.KEEP_NEAR,
                    student_ids=["s2", "s3"],
                ),
            ],
        )


@pytest.mark.asyncio
async def test_patch_roster_smart_rules_rejects_negative_revision() -> None:
    roster_id = uuid4()
    owner_user_id = uuid4()
    rosters = AsyncMock()
    smart_rules = AsyncMock()
    uow = AsyncMock()
    rosters.get_by_id.return_value = _build_roster(roster_id=roster_id, owner_user_id=owner_user_id)
    handler = PatchRosterSmartRulesHandler(uow=uow, rosters=rosters, smart_rules=smart_rules)

    with pytest.raises(DomainError, match="zero or greater"):
        await handler.handle(
            roster_id=roster_id,
            owner_user_id=owner_user_id,
            expected_revision=-1,
            seating_preferences=[],
            relationship_rules=[],
        )


@pytest.mark.asyncio
async def test_patch_roster_smart_rules_strips_false_near_teacher_preferences() -> None:
    roster_id = uuid4()
    owner_user_id = uuid4()
    rosters = AsyncMock()
    smart_rules = AsyncMock()
    uow = AsyncMock()
    rosters.get_by_id.return_value = _build_roster(roster_id=roster_id, owner_user_id=owner_user_id)
    smart_rules.save.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=1,
        seating_preferences=[],
        relationship_rules=[],
    )
    handler = PatchRosterSmartRulesHandler(uow=uow, rosters=rosters, smart_rules=smart_rules)

    await handler.handle(
        roster_id=roster_id,
        owner_user_id=owner_user_id,
        expected_revision=0,
        seating_preferences=[StudentSeatingPreference(student_id="s1", near_teacher=False)],
        relationship_rules=[],
    )

    smart_rules.save.assert_awaited_once_with(
        rules=RosterSmartRules(
            roster_id=roster_id,
            revision=0,
            seating_preferences=[],
            relationship_rules=[],
        ),
        expected_revision=0,
    )
