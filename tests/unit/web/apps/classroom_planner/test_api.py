from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.apps.classroom_planner.services import (
    ClassroomPlannerBootstrapService,
    ClassroomPlannerService,
)
from skriptoteket.domain.apps.classroom_planner.models import (
    ClassroomPlannerBootstrapPayload,
    LessonModePreset,
    RoomTemplate,
    Roster,
    Seat,
    Student,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner as api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_bootstrap_returns_payload_from_service():
    # Arrange
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerBootstrapService)
    service.get_bootstrap_payload.return_value = ClassroomPlannerBootstrapPayload(
        lesson_modes=[
            LessonModePreset(id="mode1", name="Mode 1"),
            LessonModePreset(id="mode2", name="Mode 2"),
        ],
        feature_flags={"flag1": True},
    )

    # Act
    result = await _unwrap_dishka(api.get_bootstrap)(
        service=service,
        user=user,
    )

    # Assert
    assert len(result.lesson_modes) == 2
    assert result.lesson_modes[0].id == "mode1"
    assert result.feature_flags["flag1"] is True
    service.get_bootstrap_payload.assert_awaited_once_with(owner_user_id=user.id)


# Roster API Tests


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_rosters_returns_from_service():
    # Arrange
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    now = datetime.now(timezone.utc)
    roster = Roster(
        id=uuid4(),
        owner_user_id=user.id,
        name="Class A",
        students=[Student(id="s1", display_name="Student 1")],
        created_at=now,
        updated_at=now,
    )
    service.list_rosters.return_value = [roster]

    # Act
    result = await _unwrap_dishka(api.list_rosters)(
        service=service,
        user=user,
    )

    # Assert
    assert len(result) == 1
    assert result[0].id == roster.id
    service.list_rosters.assert_awaited_once_with(owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_roster_returns_from_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    roster_id = uuid4()
    now = datetime.now(timezone.utc)
    roster = Roster(
        id=roster_id,
        owner_user_id=user.id,
        name="Class A",
        students=[],
        created_at=now,
        updated_at=now,
    )
    service.get_roster.return_value = roster

    result = await _unwrap_dishka(api.get_roster)(
        roster_id=roster_id,
        service=service,
        user=user,
    )

    assert result.id == roster_id
    service.get_roster.assert_awaited_once_with(roster_id=roster_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_roster_calls_service():
    # Arrange
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    req = api.CreateRosterRequest(name="New Class", students=[Student(id="s1", display_name="S1")])
    now = datetime.now(timezone.utc)
    roster = Roster(
        id=uuid4(),
        owner_user_id=user.id,
        name="New Class",
        students=[Student(id="s1", display_name="S1")],
        created_at=now,
        updated_at=now,
    )
    service.create_roster.return_value = roster

    # Act
    result = await _unwrap_dishka(api.create_roster)(
        request=req,
        service=service,
        user=user,
    )

    # Assert
    assert result.id == roster.id
    service.create_roster.assert_awaited_once_with(
        owner_user_id=user.id, name="New Class", students=req.students
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_roster_calls_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    roster_id = uuid4()
    req = api.UpdateRosterRequest(name="Updated", students=[])
    now = datetime.now(timezone.utc)
    roster = Roster(
        id=roster_id,
        owner_user_id=user.id,
        name="Updated",
        students=[],
        created_at=now,
        updated_at=now,
    )
    service.update_roster.return_value = roster

    result = await _unwrap_dishka(api.update_roster)(
        roster_id=roster_id,
        request=req,
        service=service,
        user=user,
    )

    assert result.name == "Updated"
    service.update_roster.assert_awaited_once_with(
        roster_id=roster_id, owner_user_id=user.id, name="Updated", students=[]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_roster_calls_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    roster_id = uuid4()

    await _unwrap_dishka(api.delete_roster)(
        roster_id=roster_id,
        service=service,
        user=user,
    )

    service.delete_roster.assert_awaited_once_with(roster_id=roster_id, owner_user_id=user.id)


# RoomTemplate API Tests


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_templates_returns_from_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=uuid4(),
        owner_user_id=user.id,
        name="Room 1",
        seats=[],
        created_at=now,
        updated_at=now,
    )
    service.list_templates.return_value = [template]

    result = await _unwrap_dishka(api.list_templates)(
        service=service,
        user=user,
    )

    assert len(result) == 1
    assert result[0].id == template.id
    service.list_templates.assert_awaited_once_with(owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_template_returns_from_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    template_id = uuid4()
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=template_id,
        owner_user_id=user.id,
        name="Room 1",
        seats=[],
        created_at=now,
        updated_at=now,
    )
    service.get_template.return_value = template

    result = await _unwrap_dishka(api.get_template)(
        template_id=template_id,
        service=service,
        user=user,
    )

    assert result.id == template_id
    service.get_template.assert_awaited_once_with(template_id=template_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_template_calls_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    req = api.CreateRoomTemplateRequest(name="Room 101", seats=[Seat(id="s1", x=0, y=0)])
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=uuid4(),
        owner_user_id=user.id,
        name="Room 101",
        seats=[Seat(id="s1", x=0, y=0)],
        created_at=now,
        updated_at=now,
    )
    service.create_template.return_value = template

    result = await _unwrap_dishka(api.create_template)(
        request=req,
        service=service,
        user=user,
    )

    assert result.id == template.id
    service.create_template.assert_awaited_once_with(
        owner_user_id=user.id, name="Room 101", seats=req.seats
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_template_calls_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    template_id = uuid4()
    req = api.UpdateRoomTemplateRequest(name="Updated Room", seats=[])
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=template_id,
        owner_user_id=user.id,
        name="Updated Room",
        seats=[],
        created_at=now,
        updated_at=now,
    )
    service.update_template.return_value = template

    result = await _unwrap_dishka(api.update_template)(
        template_id=template_id,
        request=req,
        service=service,
        user=user,
    )

    assert result.name == "Updated Room"
    service.update_template.assert_awaited_once_with(
        template_id=template_id, owner_user_id=user.id, name="Updated Room", seats=[]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_template_calls_service():
    user = make_user(role=Role.USER)
    service = AsyncMock(spec=ClassroomPlannerService)
    template_id = uuid4()

    await _unwrap_dishka(api.delete_template)(
        template_id=template_id,
        service=service,
        user=user,
    )

    service.delete_template.assert_awaited_once_with(template_id=template_id, owner_user_id=user.id)
