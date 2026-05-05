"""Roster CRUD tests for classroom planner asset lifecycle rules.

These tests cover reusable class-list updates and the save-time cascade that
removes deleted students from planner drafts and roster-owned smart rules.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateRosterHandler,
    DeleteRosterHandler,
    GetRosterHandler,
    ListRostersHandler,
    UpdateRosterHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    roster_student_cleanup,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipKind,
    RelationshipRule,
    Roster,
    RosterSmartRules,
    Student,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    RosterStudentReferenceRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from tests.fixtures.application_fixtures import FakeUow


def _clock(now: datetime) -> ClockProtocol:
    mock = Mock(spec=ClockProtocol)
    mock.now.return_value = now
    return mock


def _id_generator(roster_id) -> IdGeneratorProtocol:
    mock = Mock(spec=IdGeneratorProtocol)
    mock.new_uuid.return_value = roster_id
    return mock


def _roster(*, owner_id, roster_id, now: datetime, students: list[Student]) -> Roster:
    return Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="BF25",
        students=students,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_roster_persists_and_returns_roster() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    students = [Student(id="student-1", display_name="Ada")]
    handler = CreateRosterHandler(
        uow=FakeUow(),
        rosters=rosters,
        clock=_clock(now),
        id_generator=_id_generator(roster_id),
    )

    result = await handler.handle(owner_user_id=owner_id, name="BF25", students=students)

    assert result.id == roster_id
    assert result.owner_user_id == owner_id
    assert result.name == "BF25"
    assert result.students == students
    assert result.created_at == now
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_roster_returns_from_repo_if_owner_matches() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    roster = _roster(owner_id=owner_id, roster_id=roster_id, now=now, students=[])
    rosters.get_by_id.return_value = roster
    handler = GetRosterHandler(rosters)

    result = await handler.handle(roster_id=roster_id, owner_user_id=owner_id)

    assert result == roster


@pytest.mark.asyncio
async def test_get_roster_raises_not_found_if_owner_mismatch() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    roster_id = uuid4()
    rosters.get_by_id.return_value = _roster(
        owner_id=uuid4(),
        roster_id=roster_id,
        now=now,
        students=[],
    )
    handler = GetRosterHandler(rosters)

    with pytest.raises(DomainError) as exc:
        await handler.handle(roster_id=roster_id, owner_user_id=uuid4())

    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_list_rosters_returns_from_repo() -> None:
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    owner_id = uuid4()
    expected = [Mock(spec=Roster)]
    rosters.list_by_owner.return_value = expected
    handler = ListRostersHandler(rosters)

    result = await handler.handle(owner_user_id=owner_id)

    assert result == expected
    rosters.list_by_owner.assert_awaited_once_with(owner_user_id=owner_id)


@pytest.mark.asyncio
async def test_update_roster_allows_adding_students_when_active_draft_exists() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    student_references = AsyncMock(spec=RosterStudentReferenceRepositoryProtocol)
    smart_rules = AsyncMock(spec=RosterSmartRuleRepositoryProtocol)
    cleanup = roster_student_cleanup.RosterStudentCleanupService(
        student_references=student_references,
        smart_rules=smart_rules,
    )
    rosters.get_by_id.return_value = _roster(
        owner_id=owner_id,
        roster_id=roster_id,
        now=now,
        students=[Student(id="student-1", display_name="Ada")],
    )
    handler = UpdateRosterHandler(
        uow=FakeUow(),
        rosters=rosters,
        clock=_clock(now),
        student_cleanup=cleanup,
    )

    result = await handler.handle(
        roster_id=roster_id,
        owner_user_id=owner_id,
        name="BF25",
        students=[
            Student(id="student-1", display_name="Ada"),
            Student(id="student-2", display_name="Bea"),
        ],
    )

    assert [student.id for student in result.students] == ["student-1", "student-2"]
    rosters.save.assert_awaited_once()
    student_references.remove_for_roster.assert_not_awaited()
    smart_rules.get_by_roster_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_roster_allows_display_name_changes_when_student_ids_remain() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    student_references = AsyncMock(spec=RosterStudentReferenceRepositoryProtocol)
    smart_rules = AsyncMock(spec=RosterSmartRuleRepositoryProtocol)
    cleanup = roster_student_cleanup.RosterStudentCleanupService(
        student_references=student_references,
        smart_rules=smart_rules,
    )
    rosters.get_by_id.return_value = _roster(
        owner_id=owner_id,
        roster_id=roster_id,
        now=now,
        students=[Student(id="student-1", display_name="Ada")],
    )
    handler = UpdateRosterHandler(
        uow=FakeUow(),
        rosters=rosters,
        clock=_clock(now),
        student_cleanup=cleanup,
    )

    result = await handler.handle(
        roster_id=roster_id,
        owner_user_id=owner_id,
        name="BF25",
        students=[Student(id="student-1", display_name="Ada Lovelace")],
    )

    assert result.students == [Student(id="student-1", display_name="Ada Lovelace")]
    rosters.save.assert_awaited_once()
    student_references.remove_for_roster.assert_not_awaited()
    smart_rules.get_by_roster_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_roster_cascades_removed_students_from_drafts_and_rules() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    new_now = datetime(2026, 5, 6, tzinfo=timezone.utc)
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    student_references = AsyncMock(spec=RosterStudentReferenceRepositoryProtocol)
    smart_rules = AsyncMock(spec=RosterSmartRuleRepositoryProtocol)
    cleanup = roster_student_cleanup.RosterStudentCleanupService(
        student_references=student_references,
        smart_rules=smart_rules,
    )
    smart_rules.get_by_roster_id.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=3,
        seating_preferences=[
            StudentSeatingPreference(student_id="student-1", near_teacher=True),
            StudentSeatingPreference(student_id="student-2", near_teacher=True),
        ],
        relationship_rules=[
            RelationshipRule(
                id="keep-apart-1",
                kind=RelationshipKind.KEEP_APART,
                student_ids=["student-1", "student-2", "student-3"],
            ),
            RelationshipRule(
                id="keep-near-1",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=["student-1", "student-2"],
            ),
        ],
        fixed_seat_rules=[
            FixedSeatRule(
                id="fixed-1",
                template_id=template_id,
                student_id="student-1",
                seat_id="seat-1",
            ),
            FixedSeatRule(
                id="fixed-2",
                template_id=template_id,
                student_id="student-2",
                seat_id="seat-2",
            ),
        ],
    )
    rosters.get_by_id.return_value = _roster(
        owner_id=owner_id,
        roster_id=roster_id,
        now=now,
        students=[
            Student(id="student-1", display_name="Ada"),
            Student(id="student-2", display_name="Bea"),
            Student(id="student-3", display_name="Cleo"),
        ],
    )
    clock = _clock(new_now)
    handler = UpdateRosterHandler(
        uow=FakeUow(),
        rosters=rosters,
        clock=clock,
        student_cleanup=cleanup,
    )

    result = await handler.handle(
        roster_id=roster_id,
        owner_user_id=owner_id,
        name="BF25",
        students=[
            Student(id="student-2", display_name="Bea"),
            Student(id="student-3", display_name="Cleo"),
        ],
    )

    assert [student.id for student in result.students] == ["student-2", "student-3"]
    student_references.remove_for_roster.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
        student_ids={"student-1"},
        updated_at=new_now,
    )
    smart_rules.save.assert_awaited_once()
    saved_rules = smart_rules.save.await_args.kwargs["rules"]
    assert saved_rules.seating_preferences == [
        StudentSeatingPreference(student_id="student-2", near_teacher=True)
    ]
    assert saved_rules.relationship_rules == [
        RelationshipRule(
            id="keep-apart-1",
            kind=RelationshipKind.KEEP_APART,
            student_ids=["student-2", "student-3"],
        )
    ]
    assert saved_rules.fixed_seat_rules == [
        FixedSeatRule(
            id="fixed-2",
            template_id=template_id,
            student_id="student-2",
            seat_id="seat-2",
        )
    ]
    smart_rules.save.assert_awaited_once_with(rules=saved_rules, expected_revision=3)
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_roster_skips_rule_save_when_removed_students_are_not_referenced() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    student_references = AsyncMock(spec=RosterStudentReferenceRepositoryProtocol)
    smart_rules = AsyncMock(spec=RosterSmartRuleRepositoryProtocol)
    cleanup = roster_student_cleanup.RosterStudentCleanupService(
        student_references=student_references,
        smart_rules=smart_rules,
    )
    smart_rules.get_by_roster_id.return_value = RosterSmartRules(
        roster_id=roster_id,
        revision=3,
        seating_preferences=[StudentSeatingPreference(student_id="student-2", near_teacher=True)],
    )
    rosters.get_by_id.return_value = _roster(
        owner_id=owner_id,
        roster_id=roster_id,
        now=now,
        students=[
            Student(id="student-1", display_name="Ada"),
            Student(id="student-2", display_name="Bea"),
        ],
    )
    handler = UpdateRosterHandler(
        uow=FakeUow(),
        rosters=rosters,
        clock=_clock(now),
        student_cleanup=cleanup,
    )

    await handler.handle(
        roster_id=roster_id,
        owner_user_id=owner_id,
        name="BF25",
        students=[Student(id="student-2", display_name="Bea")],
    )

    student_references.remove_for_roster.assert_awaited_once()
    smart_rules.save.assert_not_awaited()
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_roster_calls_repo_delete() -> None:
    now = datetime(2026, 5, 5, tzinfo=timezone.utc)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)
    rosters.get_by_id.return_value = _roster(
        owner_id=owner_id,
        roster_id=roster_id,
        now=now,
        students=[],
    )
    handler = DeleteRosterHandler(FakeUow(), rosters, drafts=drafts)

    await handler.handle(roster_id=roster_id, owner_user_id=owner_id)

    drafts.delete_for_roster.assert_awaited_once_with(owner_user_id=owner_id, roster_id=roster_id)
    rosters.delete.assert_awaited_once_with(roster_id=roster_id)
