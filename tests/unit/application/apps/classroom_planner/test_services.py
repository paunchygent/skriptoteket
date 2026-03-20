from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateDraftHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    GetBootstrapHandler,
    GetDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    ListRostersHandler,
    PatchDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    PlanDraft,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from tests.fixtures.application_fixtures import FakeUow


@pytest.fixture
def uow():
    return FakeUow()


@pytest.fixture
def rosters():
    return AsyncMock(spec=RosterRepositoryProtocol)


@pytest.fixture
def templates():
    return AsyncMock(spec=RoomTemplateRepositoryProtocol)


@pytest.fixture
def drafts():
    return AsyncMock(spec=PlanDraftRepositoryProtocol)


@pytest.fixture
def now():
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def clock(now):
    mock = Mock(spec=ClockProtocol)
    mock.now.return_value = now
    return mock


@pytest.fixture
def id_generator():
    mock = Mock(spec=IdGeneratorProtocol)
    # Default to returning a new UUID each time
    mock.new_uuid.side_effect = lambda: uuid4()
    return mock


# Bootstrap Handler Tests


@pytest.mark.asyncio
async def test_bootstrap_handler_returns_payload():
    handler = GetBootstrapHandler()
    owner_id = uuid4()

    payload = await handler.handle(owner_user_id=owner_id)

    assert len(payload.lesson_modes) > 0
    assert "solver_v1" in payload.feature_flags


# Roster Handler Tests


@pytest.mark.asyncio
async def test_create_roster_persists_and_returns_roster(uow, rosters, clock, id_generator):
    handler = CreateRosterHandler(uow, rosters, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    id_generator.new_uuid.side_effect = None
    id_generator.new_uuid.return_value = roster_id
    students = [Student(id="s1", display_name="Student 1")]

    result = await handler.handle(owner_user_id=owner_id, name="Class A", students=students)

    assert result.id == roster_id
    assert result.owner_user_id == owner_id
    assert result.name == "Class A"
    assert result.students == students
    assert result.created_at == clock.now()
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_roster_returns_from_repo_if_owner_matches(rosters, now):
    handler = GetRosterHandler(rosters)
    roster_id = uuid4()
    owner_id = uuid4()
    roster = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="Test Roster",
        students=[],
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = roster

    result = await handler.handle(roster_id=roster_id, owner_user_id=owner_id)

    assert result == roster


@pytest.mark.asyncio
async def test_get_roster_raises_not_found_if_owner_mismatch(rosters, now):
    handler = GetRosterHandler(rosters)
    roster_id = uuid4()
    roster = Roster(
        id=roster_id,
        owner_user_id=uuid4(),
        name="Test Roster",
        students=[],
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = roster

    with pytest.raises(DomainError) as exc:
        await handler.handle(roster_id=roster_id, owner_user_id=uuid4())
    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_list_rosters_returns_from_repo(rosters):
    handler = ListRostersHandler(rosters)
    owner_id = uuid4()
    expected = [Mock(spec=Roster)]
    rosters.list_by_owner.return_value = expected

    result = await handler.handle(owner_user_id=owner_id)

    assert result == expected
    rosters.list_by_owner.assert_awaited_once_with(owner_user_id=owner_id)


@pytest.mark.asyncio
async def test_update_roster_updates_and_saves(uow, rosters, now, clock):
    handler = UpdateRosterHandler(uow, rosters, clock)
    owner_id = uuid4()
    roster_id = uuid4()
    old_roster = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="Old Name",
        students=[],
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = old_roster
    new_now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    clock.now.return_value = new_now
    new_students = [Student(id="s2", display_name="Student 2")]

    result = await handler.handle(
        roster_id=roster_id, owner_user_id=owner_id, name="New Name", students=new_students
    )

    assert result.name == "New Name"
    assert result.students == new_students
    assert result.updated_at == new_now
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_roster_calls_repo_delete(uow, rosters, now):
    handler = DeleteRosterHandler(uow, rosters)
    owner_id = uuid4()
    roster_id = uuid4()
    roster = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="To Delete",
        students=[],
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = roster

    await handler.handle(roster_id=roster_id, owner_user_id=owner_id)

    rosters.delete.assert_awaited_once_with(roster_id=roster_id)


# RoomTemplate Handler Tests


@pytest.mark.asyncio
async def test_create_template_persists_and_returns_template(uow, templates, clock, id_generator):
    handler = CreateRoomTemplateHandler(uow, templates, clock, id_generator)
    owner_id = uuid4()
    template_id = uuid4()
    id_generator.new_uuid.side_effect = None
    id_generator.new_uuid.return_value = template_id
    seats = [Seat(id="seat1", x=0, y=0)]

    result = await handler.handle(owner_user_id=owner_id, name="Room 101", seats=seats)

    assert result.id == template_id
    assert result.name == "Room 101"
    assert result.seats == seats
    assert result.created_at == clock.now()
    templates.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_template_returns_from_repo_if_owner_matches(templates, now):
    handler = GetRoomTemplateHandler(templates)
    template_id = uuid4()
    owner_id = uuid4()
    template = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="Test Template",
        seats=[],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = template

    result = await handler.handle(template_id=template_id, owner_user_id=owner_id)

    assert result == template


@pytest.mark.asyncio
async def test_update_template_updates_and_saves(uow, templates, now, clock):
    handler = UpdateRoomTemplateHandler(uow, templates, clock)
    owner_id = uuid4()
    template_id = uuid4()
    old_template = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="Old Template",
        seats=[],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = old_template
    new_now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    clock.now.return_value = new_now
    new_seats = [Seat(id="s2", x=1, y=1)]

    result = await handler.handle(
        template_id=template_id, owner_user_id=owner_id, name="New Name", seats=new_seats
    )

    assert result.name == "New Name"
    assert result.seats == new_seats
    assert result.updated_at == new_now
    templates.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_template_calls_repo_delete(uow, templates, now):
    handler = DeleteRoomTemplateHandler(uow, templates)
    owner_id = uuid4()
    template_id = uuid4()
    template = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="To Delete",
        seats=[],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = template

    await handler.handle(template_id=template_id, owner_user_id=owner_id)

    templates.delete.assert_awaited_once_with(template_id=template_id)


# PlanDraft Handler Tests


@pytest.mark.asyncio
async def test_create_draft_persists_and_returns_draft(
    uow, rosters, templates, drafts, clock, id_generator
):
    handler = CreateDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    draft_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    id_generator.new_uuid.side_effect = None
    id_generator.new_uuid.return_value = draft_id

    # Mock dependencies existence
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        template_id=template_id,
        lesson_mode_id="standard",
        group_assignments=[GroupAssignment(student_id="s1", group_id="g1")],
        seat_assignments=[SeatAssignment(student_id="s2", seat_id="seat1")],
    )

    assert result.id == draft_id
    assert result.owner_user_id == owner_id
    assert result.roster_id == roster_id
    assert result.template_id == template_id
    assert result.lesson_mode_id == "standard"
    assert len(result.group_assignments) == 1
    assert len(result.seat_assignments) == 1
    assert result.created_at == clock.now()
    drafts.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_draft_returns_from_repo_if_owner_matches(drafts, now):
    handler = GetDraftHandler(drafts)
    draft_id = uuid4()
    owner_id = uuid4()
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        template_id=uuid4(),
        lesson_mode_id="standard",
        group_assignments=[],
        seat_assignments=[],
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.return_value = draft

    result = await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert result == draft


@pytest.mark.asyncio
async def test_patch_draft_updates_and_saves(uow, drafts, now, clock):
    handler = PatchDraftHandler(uow, drafts, clock)
    owner_id = uuid4()
    draft_id = uuid4()
    old_draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        template_id=uuid4(),
        lesson_mode_id="standard",
        revision=0,
        group_assignments=[GroupAssignment(student_id="s1", group_id="g1")],
        seat_assignments=[],
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.return_value = old_draft
    new_now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    clock.now.return_value = new_now

    result = await handler.handle(
        draft_id=draft_id,
        owner_user_id=owner_id,
        expected_revision=0,
        group_assignments=[GroupAssignment(student_id="s1", group_id="g2")],
        seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat1")],
    )

    assert result.revision == 1
    assert len(result.group_assignments) == 1
    assert result.group_assignments[0].group_id == "g2"
    assert result.updated_at == new_now
    drafts.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_draft_raises_conflict_if_revision_mismatch(uow, drafts, now, clock):
    handler = PatchDraftHandler(uow, drafts, clock)
    owner_id = uuid4()
    draft_id = uuid4()
    old_draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        template_id=uuid4(),
        lesson_mode_id="standard",
        revision=5,
        group_assignments=[],
        seat_assignments=[],
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.return_value = old_draft

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            draft_id=draft_id,
            owner_user_id=owner_id,
            expected_revision=4,  # Mismatch
        )
    assert exc.value.code == ErrorCode.CONFLICT
