from datetime import datetime, timezone
from unittest.mock import AsyncMock
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
    ListRoomTemplatesHandler,
    ListRostersHandler,
    PatchDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerBootstrapPayload,
    GroupAssignment,
    LessonModePreset,
    PlanDraft,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
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
async def test_get_bootstrap_returns_payload_from_handler():
    # Arrange
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetBootstrapHandler)
    handler.handle.return_value = ClassroomPlannerBootstrapPayload(
        lesson_modes=[
            LessonModePreset(id="mode1", name="Mode 1"),
            LessonModePreset(id="mode2", name="Mode 2"),
        ],
        feature_flags={"flag1": True},
    )

    # Act
    result = await _unwrap_dishka(api.get_bootstrap)(
        handler=handler,
        user=user,
    )

    # Assert
    assert len(result.lesson_modes) == 2
    assert result.lesson_modes[0].id == "mode1"
    assert result.feature_flags["flag1"] is True
    handler.handle.assert_awaited_once_with(owner_user_id=user.id)


# Roster API Tests


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_rosters_returns_from_handler():
    # Arrange
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=ListRostersHandler)
    now = datetime.now(timezone.utc)
    roster = Roster(
        id=uuid4(),
        owner_user_id=user.id,
        name="Class A",
        students=[Student(id="s1", display_name="Student 1")],
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = [roster]

    # Act
    result = await _unwrap_dishka(api.list_rosters)(
        handler=handler,
        user=user,
    )

    # Assert
    assert len(result) == 1
    assert result[0].id == roster.id
    handler.handle.assert_awaited_once_with(owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_roster_returns_from_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetRosterHandler)
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
    handler.handle.return_value = roster

    result = await _unwrap_dishka(api.get_roster)(
        roster_id=roster_id,
        handler=handler,
        user=user,
    )

    assert result.id == roster_id
    handler.handle.assert_awaited_once_with(roster_id=roster_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_roster_calls_handler():
    # Arrange
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=CreateRosterHandler)
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
    handler.handle.return_value = roster

    # Act
    result = await _unwrap_dishka(api.create_roster)(
        request=req,
        handler=handler,
        user=user,
    )

    # Assert
    assert result.id == roster.id
    handler.handle.assert_awaited_once_with(
        owner_user_id=user.id, name="New Class", students=req.students
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_roster_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=UpdateRosterHandler)
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
    handler.handle.return_value = roster

    result = await _unwrap_dishka(api.update_roster)(
        roster_id=roster_id,
        request=req,
        handler=handler,
        user=user,
    )

    assert result.name == "Updated"
    handler.handle.assert_awaited_once_with(
        roster_id=roster_id, owner_user_id=user.id, name="Updated", students=[]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_roster_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=DeleteRosterHandler)
    roster_id = uuid4()

    await _unwrap_dishka(api.delete_roster)(
        roster_id=roster_id,
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(roster_id=roster_id, owner_user_id=user.id)


# RoomTemplate API Tests


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_templates_returns_from_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=ListRoomTemplatesHandler)
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=uuid4(),
        owner_user_id=user.id,
        name="Room 1",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = [template]

    result = await _unwrap_dishka(api.list_templates)(
        handler=handler,
        user=user,
    )

    assert len(result) == 1
    assert result[0].id == template.id
    handler.handle.assert_awaited_once_with(owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_template_returns_from_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetRoomTemplateHandler)
    template_id = uuid4()
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=template_id,
        owner_user_id=user.id,
        name="Room 1",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = template

    result = await _unwrap_dishka(api.get_template)(
        template_id=template_id,
        handler=handler,
        user=user,
    )

    assert result.id == template_id
    handler.handle.assert_awaited_once_with(template_id=template_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_template_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=CreateRoomTemplateHandler)
    req = api.CreateRoomTemplateRequest(name="Room 101", seats=[Seat(id="s1", x=0, y=0)])
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=uuid4(),
        owner_user_id=user.id,
        name="Room 101",
        seats=[Seat(id="s1", x=0, y=0)],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = template

    result = await _unwrap_dishka(api.create_template)(
        request=req,
        handler=handler,
        user=user,
    )

    assert result.id == template.id
    handler.handle.assert_awaited_once_with(
        owner_user_id=user.id,
        name="Room 101",
        seats=req.seats,
        fixtures=[],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_template_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=UpdateRoomTemplateHandler)
    template_id = uuid4()
    req = api.UpdateRoomTemplateRequest(name="Updated Room", seats=[])
    now = datetime.now(timezone.utc)
    template = RoomTemplate(
        id=template_id,
        owner_user_id=user.id,
        name="Updated Room",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = template

    result = await _unwrap_dishka(api.update_template)(
        template_id=template_id,
        request=req,
        handler=handler,
        user=user,
    )

    assert result.name == "Updated Room"
    handler.handle.assert_awaited_once_with(
        template_id=template_id,
        owner_user_id=user.id,
        name="Updated Room",
        seats=[],
        fixtures=[],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_template_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=DeleteRoomTemplateHandler)
    template_id = uuid4()

    await _unwrap_dishka(api.delete_template)(
        template_id=template_id,
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(template_id=template_id, owner_user_id=user.id)


# PlanDraft API Tests


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=CreateDraftHandler)
    req = api.CreatePlanDraftRequest(
        roster_id=uuid4(),
        template_id=uuid4(),
        lesson_mode_id="seating",
    )
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=user.id,
        roster_id=req.roster_id,
        template_id=req.template_id,
        lesson_mode_id=req.lesson_mode_id,
        revision=0,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api.create_draft)(
        request=req,
        handler=handler,
        user=user,
    )

    assert result.id == draft.id
    handler.handle.assert_awaited_once_with(
        owner_user_id=user.id,
        roster_id=req.roster_id,
        template_id=req.template_id,
        lesson_mode_id=req.lesson_mode_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_draft_returns_from_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetDraftHandler)
    draft_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        template_id=uuid4(),
        lesson_mode_id="seating",
        revision=0,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api.get_draft)(
        draft_id=draft_id,
        handler=handler,
        user=user,
    )

    assert result.id == draft_id
    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=PatchDraftHandler)
    draft_id = uuid4()
    req = api.UpdatePlanDraftRequest(
        expected_revision=0,
        group_assignments=[api.GroupAssignmentDto(student_id="s1", group_id="g2")],
        seat_assignments=[api.SeatAssignmentDto(student_id="s1", seat_id="seat1")],
    )
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        template_id=uuid4(),
        lesson_mode_id="seating",
        revision=1,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api.update_draft)(
        draft_id=draft_id,
        request=req,
        handler=handler,
        user=user,
    )

    assert result.revision == 1
    handler.handle.assert_awaited_once_with(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=0,
        lesson_mode_id=None,
        groups=None,
        group_assignments=[GroupAssignment(student_id="s1", group_id="g2")],
        seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat1")],
        student_planning_meta=None,
        pair_constraints=None,
        planning_profile=None,
    )
