"""Repository tests for roster-owned classroom planner smart rules."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipKind,
    RelationshipRule,
    RosterSmartRules,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.repositories.classroom_planner_smart_rules import (
    PostgreSQLRosterSmartRuleRepository,
)


def _scalar_result(models: list[object]) -> Mock:
    result = Mock()
    scalars = result.scalars.return_value
    scalars.all.return_value = models
    return result


def _scalar_one_or_none_result(value: object | None) -> Mock:
    result = Mock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_get_by_roster_id_returns_empty_rules_when_no_rows_exist() -> None:
    session = AsyncMock()
    session.execute.side_effect = [_scalar_one_or_none_result(None)]
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()

    result = await repo.get_by_roster_id(roster_id=roster_id)

    assert result == RosterSmartRules(roster_id=roster_id, revision=0)


@pytest.mark.asyncio
async def test_get_by_roster_id_maps_stored_rows_to_domain_rules() -> None:
    session = AsyncMock()
    roster_id = uuid4()
    root_row = Mock(revision=4)
    seating_row = Mock(student_id="student-1", near_teacher=True)
    relation_row = Mock(
        rule_id="rule-1",
        kind=RelationshipKind.KEEP_APART.value,
        student_ids=["student-1", "student-2"],
    )
    fixed_row = Mock(
        rule_id="fixed-1",
        template_id=roster_id,
        student_id="student-1",
        seat_id="seat-1",
    )
    session.execute.side_effect = [
        _scalar_one_or_none_result(root_row),
        _scalar_result([seating_row]),
        _scalar_result([relation_row]),
        _scalar_result([fixed_row]),
    ]
    repo = PostgreSQLRosterSmartRuleRepository(session)

    result = await repo.get_by_roster_id(roster_id=roster_id)

    assert result == RosterSmartRules(
        roster_id=roster_id,
        revision=4,
        seating_preferences=[StudentSeatingPreference(student_id="student-1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["student-1", "student-2"],
            )
        ],
        fixed_seat_rules=[
            FixedSeatRule(
                id="fixed-1",
                template_id=roster_id,
                student_id="student-1",
                seat_id="seat-1",
            )
        ],
    )


@pytest.mark.asyncio
async def test_get_by_roster_id_filters_false_near_teacher_rows_from_persisted_state() -> None:
    session = AsyncMock()
    root_row = Mock(revision=4)
    seating_row = Mock(student_id="student-1", near_teacher=False)
    session.execute.side_effect = [
        _scalar_one_or_none_result(root_row),
        _scalar_result([seating_row]),
        _scalar_result([]),
        _scalar_result([]),
    ]
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()

    result = await repo.get_by_roster_id(roster_id=roster_id)

    assert result == RosterSmartRules(
        roster_id=roster_id,
        revision=4,
        seating_preferences=[],
        relationship_rules=[],
    )


@pytest.mark.asyncio
async def test_save_inserts_initial_revision_and_replaces_rules() -> None:
    session = AsyncMock()
    session.add_all = Mock()
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()
    rules = RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[StudentSeatingPreference(student_id="student-1", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="rule-1",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=["student-1", "student-2"],
            )
        ],
        fixed_seat_rules=[
            FixedSeatRule(
                id="fixed-1",
                template_id=roster_id,
                student_id="student-2",
                seat_id="seat-7",
            )
        ],
    )
    session.execute.side_effect = [
        _scalar_one_or_none_result(1),
        Mock(),
        Mock(),
        Mock(),
    ]

    persisted = await repo.save(rules=rules, expected_revision=0)

    assert persisted.revision == 1
    assert session.execute.await_count == 4
    seating_models = session.add_all.call_args_list[0].args[0]
    relationship_models = session.add_all.call_args_list[1].args[0]
    fixed_seat_models = session.add_all.call_args_list[2].args[0]
    assert len(seating_models) == 1
    assert seating_models[0].roster_id == roster_id
    assert seating_models[0].student_id == "student-1"
    assert seating_models[0].near_teacher is True
    assert len(relationship_models) == 1
    assert relationship_models[0].roster_id == roster_id
    assert relationship_models[0].rule_id == "rule-1"
    assert relationship_models[0].kind == RelationshipKind.KEEP_NEAR.value
    assert relationship_models[0].student_ids == ["student-1", "student-2"]
    assert len(fixed_seat_models) == 1
    assert fixed_seat_models[0].roster_id == roster_id
    assert fixed_seat_models[0].rule_id == "fixed-1"
    assert fixed_seat_models[0].template_id == roster_id
    assert fixed_seat_models[0].student_id == "student-2"
    assert fixed_seat_models[0].seat_id == "seat-7"
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_save_does_not_persist_false_near_teacher_preferences() -> None:
    session = AsyncMock()
    session.add_all = Mock()
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()
    rules = RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[StudentSeatingPreference(student_id="student-1", near_teacher=False)],
        relationship_rules=[],
    )
    session.execute.side_effect = [
        _scalar_one_or_none_result(1),
        Mock(),
        Mock(),
        Mock(),
    ]

    persisted = await repo.save(rules=rules, expected_revision=0)

    assert persisted.revision == 1
    seating_models = session.add_all.call_args_list[0].args[0]
    assert seating_models == []


@pytest.mark.asyncio
async def test_save_updates_existing_revision_when_expected_revision_matches() -> None:
    session = AsyncMock()
    session.add_all = Mock()
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()
    rules = RosterSmartRules(
        roster_id=roster_id,
        revision=3,
        seating_preferences=[],
        relationship_rules=[],
    )
    session.execute.side_effect = [
        _scalar_one_or_none_result(4),
        Mock(),
        Mock(),
        Mock(),
    ]

    persisted = await repo.save(rules=rules, expected_revision=3)

    assert persisted.revision == 4
    assert session.execute.await_count == 4


@pytest.mark.asyncio
async def test_save_advances_existing_zero_revision_root_without_false_conflict() -> None:
    session = AsyncMock()
    session.add_all = Mock()
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()
    rules = RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[],
        relationship_rules=[],
    )
    session.execute.side_effect = [
        _scalar_one_or_none_result(None),
        _scalar_one_or_none_result(1),
        Mock(),
        Mock(),
        Mock(),
    ]

    persisted = await repo.save(rules=rules, expected_revision=0)

    assert persisted.revision == 1
    assert session.execute.await_count == 5
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_save_raises_conflict_when_revision_mismatches() -> None:
    session = AsyncMock()
    session.add_all = Mock()
    repo = PostgreSQLRosterSmartRuleRepository(session)
    roster_id = uuid4()
    rules = RosterSmartRules(
        roster_id=roster_id,
        revision=2,
        seating_preferences=[],
        relationship_rules=[],
    )
    current_root = Mock(revision=5)
    session.execute.side_effect = [
        _scalar_one_or_none_result(None),
        _scalar_one_or_none_result(current_root),
        _scalar_result([]),
        _scalar_result([]),
        _scalar_result([]),
    ]

    with pytest.raises(DomainError, match="Expected 2, got 5"):
        await repo.save(rules=rules, expected_revision=2)
