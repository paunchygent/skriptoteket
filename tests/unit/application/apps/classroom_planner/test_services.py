from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.apps.classroom_planner.services import (
    ClassroomPlannerBootstrapService,
    ClassroomPlannerService,
)
from skriptoteket.domain.apps.classroom_planner.models import RoomTemplate, Roster, Seat, Student
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner import (
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


@pytest.fixture
def service(uow, rosters, templates, clock, id_generator):
    return ClassroomPlannerService(
        uow=uow, rosters=rosters, templates=templates, clock=clock, id_generator=id_generator
    )


# Bootstrap Service Tests


@pytest.mark.asyncio
async def test_bootstrap_service_returns_payload():
    service = ClassroomPlannerBootstrapService()
    owner_id = uuid4()

    payload = await service.get_bootstrap_payload(owner_user_id=owner_id)

    assert len(payload.lesson_modes) > 0
    assert "solver_v1" in payload.feature_flags


# Roster CRUD Tests


@pytest.mark.asyncio
async def test_create_roster_persists_and_returns_roster(service, rosters, clock, id_generator):
    # Arrange
    owner_id = uuid4()
    roster_id = uuid4()
    id_generator.new_uuid.side_effect = None
    id_generator.new_uuid.return_value = roster_id
    students = [Student(id="s1", display_name="Student 1")]

    # Act
    result = await service.create_roster(owner_user_id=owner_id, name="Class A", students=students)

    # Assert
    assert result.id == roster_id
    assert result.owner_user_id == owner_id
    assert result.name == "Class A"
    assert result.students == students
    assert result.created_at == clock.now()
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_roster_returns_from_repo_if_owner_matches(service, rosters, now):
    # Arrange
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

    # Act
    result = await service.get_roster(roster_id=roster_id, owner_user_id=owner_id)

    # Assert
    assert result == roster


@pytest.mark.asyncio
async def test_get_roster_raises_not_found_if_owner_mismatch(service, rosters, now):
    # Arrange
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

    # Act & Assert
    with pytest.raises(DomainError) as exc:
        await service.get_roster(roster_id=roster_id, owner_user_id=uuid4())
    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_list_rosters_returns_from_repo(service, rosters):
    owner_id = uuid4()
    expected = [Mock(spec=Roster)]
    rosters.list_by_owner.return_value = expected

    result = await service.list_rosters(owner_user_id=owner_id)

    assert result == expected
    rosters.list_by_owner.assert_awaited_once_with(owner_user_id=owner_id)


@pytest.mark.asyncio
async def test_update_roster_updates_and_saves(service, rosters, now, clock):
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

    result = await service.update_roster(
        roster_id=roster_id, owner_user_id=owner_id, name="New Name", students=new_students
    )

    assert result.name == "New Name"
    assert result.students == new_students
    assert result.updated_at == new_now
    rosters.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_roster_calls_repo_delete(service, rosters, now):
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

    await service.delete_roster(roster_id=roster_id, owner_user_id=owner_id)

    rosters.delete.assert_awaited_once_with(roster_id=roster_id)


# RoomTemplate CRUD Tests


@pytest.mark.asyncio
async def test_create_template_persists_and_returns_template(
    service, templates, clock, id_generator
):
    # Arrange
    owner_id = uuid4()
    template_id = uuid4()
    id_generator.new_uuid.side_effect = None
    id_generator.new_uuid.return_value = template_id
    seats = [Seat(id="seat1", x=0, y=0)]

    # Act
    result = await service.create_template(owner_user_id=owner_id, name="Room 101", seats=seats)

    # Assert
    assert result.id == template_id
    assert result.name == "Room 101"
    assert result.seats == seats
    assert result.created_at == clock.now()
    templates.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_template_returns_from_repo_if_owner_matches(service, templates, now):
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

    result = await service.get_template(template_id=template_id, owner_user_id=owner_id)

    assert result == template


@pytest.mark.asyncio
async def test_update_template_updates_and_saves(service, templates, now, clock):
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

    result = await service.update_template(
        template_id=template_id, owner_user_id=owner_id, name="New Name", seats=new_seats
    )

    assert result.name == "New Name"
    assert result.seats == new_seats
    assert result.updated_at == new_now
    templates.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_template_calls_repo_delete(service, templates, now):
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

    await service.delete_template(template_id=template_id, owner_user_id=owner_id)

    templates.delete.assert_awaited_once_with(template_id=template_id)
