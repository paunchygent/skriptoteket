from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    GetDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    ListRostersHandler,
    PatchDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
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
    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)
    drafts.has_active_for_roster.return_value = False
    handler = DeleteRosterHandler(uow, rosters, drafts=drafts)
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

    result = await handler.handle(
        owner_user_id=owner_id,
        name="Room 101",
        seats=seats,
        fixtures=[],
    )

    assert result.id == template_id
    assert result.name == "Room 101"
    assert result.seats == seats
    assert result.fixtures == []
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
        fixtures=[],
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
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = old_template
    new_now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    clock.now.return_value = new_now
    new_seats = [Seat(id="s2", x=1, y=1)]

    result = await handler.handle(
        template_id=template_id,
        owner_user_id=owner_id,
        name="New Name",
        seats=new_seats,
        fixtures=[],
    )

    assert result.name == "New Name"
    assert result.seats == new_seats
    assert result.updated_at == new_now
    templates.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_template_calls_repo_delete(uow, templates, now):
    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)
    drafts.has_active_for_template.return_value = False
    handler = DeleteRoomTemplateHandler(
        uow,
        templates,
        drafts=drafts,
    )
    owner_id = uuid4()
    template_id = uuid4()
    template = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="To Delete",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = template

    await handler.handle(template_id=template_id, owner_user_id=owner_id)

    templates.delete.assert_awaited_once_with(template_id=template_id)


@pytest.mark.asyncio
async def test_get_draft_returns_from_repo_if_owner_matches(drafts, now):
    handler = GetDraftHandler(drafts)
    draft_id = uuid4()
    owner_id = uuid4()
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.return_value = draft

    result = await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert result == draft


@pytest.mark.asyncio
async def test_patch_draft_updates_and_saves(uow, drafts, rosters, templates, now, clock):
    handler = PatchDraftHandler(uow, drafts, rosters, templates, clock)
    owner_id = uuid4()
    draft_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    new_now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    old_draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_workspace.side_effect = [
        DraftWorkspace(
            draft=old_draft,
            groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=0)],
            group_assignments=[GroupAssignment(student_id="s1", group_id="group-1")],
            seat_assignments=[],
            student_planning_meta=[],
        ),
        DraftWorkspace(
            draft=old_draft.model_copy(update={"revision": 1, "updated_at": new_now}),
            groups=[
                DraftGroup(id="group-1", name="Grupp 1", sort_order=0),
                DraftGroup(id="group-2", name="Grupp 2", sort_order=1),
            ],
            group_assignments=[GroupAssignment(student_id="s1", group_id="group-2")],
            seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat1")],
            student_planning_meta=[],
        ),
    ]
    rosters.get_by_id.return_value = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="Klass",
        students=[Student(id="s1", display_name="Student 1")],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="Rum",
        seats=[Seat(id="seat1", x=0, y=0)],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    clock.now.return_value = new_now

    result = await handler.handle(
        draft_id=draft_id,
        owner_user_id=owner_id,
        expected_revision=0,
        groups=[
            DraftGroup(id="group-1", name="Grupp 1", sort_order=0),
            DraftGroup(id="group-2", name="Grupp 2", sort_order=1),
        ],
        group_assignments=[GroupAssignment(student_id="s1", group_id="group-2")],
        seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat1")],
    )

    assert result.draft.revision == 1
    assert result.draft.updated_at == new_now
    assert result.group_assignments[0].group_id == "group-2"
    drafts.save_workspace.assert_awaited_once()
    saved_workspace = drafts.save_workspace.await_args.kwargs["workspace"]
    assert saved_workspace.group_assignments[0].group_id == "group-2"
    assert saved_workspace.seat_assignments[0].seat_id == "seat1"


@pytest.mark.asyncio
async def test_patch_draft_rejects_inactive_draft(uow, drafts, rosters, templates, now, clock):
    handler = PatchDraftHandler(uow, drafts, rosters, templates, clock)
    owner_id = uuid4()
    draft_id = uuid4()
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=PlanDraft(
            id=draft_id,
            owner_user_id=owner_id,
            roster_id=uuid4(),
            draft_kind=PlanDraftKind.SEATING,
            template_id=uuid4(),
            status=PlanDraftStatus.ABANDONED,
            revision=5,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        groups=[],
        group_assignments=[],
        seat_assignments=[],
        student_planning_meta=[],
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert exc.value.code == ErrorCode.CONFLICT
    drafts.save_workspace.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_draft_raises_conflict_if_revision_mismatch(
    uow, drafts, rosters, templates, now, clock
):
    handler = PatchDraftHandler(uow, drafts, rosters, templates, clock)
    owner_id = uuid4()
    draft_id = uuid4()
    old_draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=5,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=old_draft,
        groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=0)],
        group_assignments=[],
        seat_assignments=[],
        student_planning_meta=[],
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            draft_id=draft_id,
            owner_user_id=owner_id,
            expected_revision=4,  # Mismatch
        )
    assert exc.value.code == ErrorCode.CONFLICT
