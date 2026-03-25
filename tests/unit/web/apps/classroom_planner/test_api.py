from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    AbandonDraftHandler,
    ActivateGroupingHistoryDraftHandler,
    ActivateSeatingHistoryDraftHandler,
    CreateGroupingDraftHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    CreateSeatingDraftHandler,
    DeleteHistoricGroupingDraftHandler,
    DeleteHistoricSeatingDraftHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    GetDraftHandler,
    GetResumableDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    ListRoomTemplatesHandler,
    ListRostersHandler,
    PatchDraftHandler,
    RedoDraftHandler,
    ResolveDraftHandler,
    UndoDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    ResumablePlanDraft,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner as api
from skriptoteket.web.api.v1 import apps_classroom_planner_grouping as api_grouping
from skriptoteket.web.api.v1 import apps_classroom_planner_seating as api_seating
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_activate_grouping_history_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=ActivateGroupingHistoryDraftHandler)
    draft_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=4,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api_grouping.activate_grouping_history_draft)(
        draft_id=draft_id,
        handler=handler,
        user=user,
    )

    assert result.id == draft_id
    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_historic_grouping_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=DeleteHistoricGroupingDraftHandler)
    draft_id = uuid4()

    await _unwrap_dishka(api_grouping.delete_historic_grouping_draft)(
        draft_id=draft_id,
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=CreateSeatingDraftHandler)
    now = datetime.now(timezone.utc)
    roster_id = uuid4()
    template_id = uuid4()
    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=user.id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api_seating.create_seating_draft)(
        request=api_seating.CreateSeatingDraftRequest(
            roster_id=roster_id,
            template_id=template_id,
        ),
        handler=handler,
        user=user,
    )

    assert result.id == draft.id
    handler.handle.assert_awaited_once_with(
        owner_user_id=user.id,
        roster_id=roster_id,
        template_id=template_id,
    )


@pytest.mark.unit
def test_create_seating_draft_request_requires_template_id():
    with pytest.raises(ValidationError):
        api_seating.CreateSeatingDraftRequest(
            roster_id=uuid4(),
            template_id=None,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_activate_seating_history_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=ActivateSeatingHistoryDraftHandler)
    draft_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=3,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api_seating.activate_seating_history_draft)(
        draft_id=draft_id,
        handler=handler,
        user=user,
    )

    assert result.id == draft_id
    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_historic_seating_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=DeleteHistoricSeatingDraftHandler)
    draft_id = uuid4()

    await _unwrap_dishka(api_seating.delete_historic_seating_draft)(
        draft_id=draft_id,
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


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
        grid_cols=14,
        grid_rows=9,
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
        grid_cols=14,
        grid_rows=9,
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
async def test_get_draft_returns_from_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetDraftHandler)
    draft_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
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
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=1,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    workspace = ClassroomPlannerWorkspace(
        draft=draft,
        roster=Roster(
            id=draft.roster_id,
            owner_user_id=user.id,
            name="Klass A",
            students=[],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=draft.template_id,
            owner_user_id=user.id,
            name="Rum 1",
            seats=[],
            fixtures=[],
            created_at=now,
            updated_at=now,
        ),
        groups=[],
        group_assignments=[],
        seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat1")],
        student_planning_meta=[],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )
    handler.handle.return_value = workspace

    result = await _unwrap_dishka(api.update_draft)(
        draft_id=draft_id,
        request=req,
        handler=handler,
        user=user,
    )

    assert result.draft.revision == 1
    assert result.history_status.can_undo is True
    handler.handle.assert_awaited_once_with(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=0,
        smart_enabled=None,
        groups=None,
        group_assignments=[GroupAssignment(student_id="s1", group_id="g2")],
        seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat1")],
        student_planning_meta=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=ResolveDraftHandler)
    req = api.ResolvePlanDraftRequest(
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
    )
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=user.id,
        roster_id=req.roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=req.template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api.resolve_draft)(
        request=req,
        handler=handler,
        user=user,
    )

    assert result.id == draft.id
    handler.handle.assert_awaited_once_with(
        owner_user_id=user.id,
        roster_id=req.roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=req.template_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=CreateGroupingDraftHandler)
    req = api_grouping.CreateGroupingDraftRequest(
        roster_id=uuid4(),
        template_id=uuid4(),
    )
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=user.id,
        roster_id=req.roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=req.template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api_grouping.create_grouping_draft)(
        request=req,
        handler=handler,
        user=user,
    )

    assert result.id == draft.id
    handler.handle.assert_awaited_once_with(
        owner_user_id=user.id,
        roster_id=req.roster_id,
        template_id=req.template_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_abandon_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=AbandonDraftHandler)
    draft_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ABANDONED,
        revision=1,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = draft

    result = await _unwrap_dishka(api.abandon_draft)(
        draft_id=draft_id,
        handler=handler,
        user=user,
    )

    assert result.id == draft_id
    assert result.status == PlanDraftStatus.ABANDONED.value
    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_resumable_draft_returns_serialized_payload():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=GetResumableDraftHandler)
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=3,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    handler.handle.return_value = ResumablePlanDraft(
        draft=draft,
        roster_name="SA24D",
        template_name="Sal 101",
    )

    result = await _unwrap_dishka(api.get_resumable_draft)(
        handler=handler,
        user=user,
    )

    assert result is not None
    assert result.draft.id == draft.id
    assert result.roster_name == "SA24D"
    assert result.template_name == "Sal 101"
    handler.handle.assert_awaited_once_with(owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_undo_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=UndoDraftHandler)
    roster_repo = AsyncMock()
    template_repo = AsyncMock()
    draft_id = uuid4()
    now = datetime.now(timezone.utc)

    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=1,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    workspace = DraftWorkspace(
        draft=draft,
        groups=[],
        group_assignments=[],
        seat_assignments=[SeatAssignment(student_id="s1", seat_id="seat-1")],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )
    handler.handle.return_value = workspace
    roster_repo.get_by_id.return_value = Roster(
        id=draft.roster_id,
        owner_user_id=user.id,
        name="Class",
        students=[],
        created_at=now,
        updated_at=now,
    )
    template_repo.get_by_id.return_value = RoomTemplate(
        id=draft.template_id,
        owner_user_id=user.id,
        name="Sal 101",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )

    result = await _unwrap_dishka(api.undo_draft)(
        draft_id=draft_id,
        handler=handler,
        rosters=roster_repo,
        templates=template_repo,
        user=user,
    )

    assert result.draft.id == draft_id
    assert result.history_status.can_undo is True
    assert result.template is not None
    assert result.seat_assignments == [api.SeatAssignmentDto(student_id="s1", seat_id="seat-1")]
    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_undo_draft_returns_latest_template_state_after_separate_room_edits():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=UndoDraftHandler)
    roster_repo = AsyncMock()
    template_repo = AsyncMock()
    draft_id = uuid4()
    template_id = uuid4()
    now = datetime.now(timezone.utc)

    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    workspace = DraftWorkspace(
        draft=draft,
        groups=[],
        group_assignments=[],
        seat_assignments=[],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=True),
    )
    handler.handle.return_value = workspace
    roster_repo.get_by_id.return_value = Roster(
        id=draft.roster_id,
        owner_user_id=user.id,
        name="Class",
        students=[],
        created_at=now,
        updated_at=now,
    )
    template_repo.get_by_id.return_value = RoomTemplate(
        id=template_id,
        owner_user_id=user.id,
        name="Sal 101 uppdaterad",
        seats=[Seat(id="seat-1", x=320, y=180, zone="window")],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )

    result = await _unwrap_dishka(api.undo_draft)(
        draft_id=draft_id,
        handler=handler,
        rosters=roster_repo,
        templates=template_repo,
        user=user,
    )

    assert result.template is not None
    assert result.template.name == "Sal 101 uppdaterad"
    assert result.template.seats == [api.SeatDto(id="seat-1", x=320, y=180, zone="window")]
    assert result.seat_assignments == []
    template_repo.get_by_id.assert_awaited_once_with(template_id=template_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redo_draft_calls_handler():
    user = make_user(role=Role.USER)
    handler = AsyncMock(spec=RedoDraftHandler)
    roster_repo = AsyncMock()
    template_repo = AsyncMock()
    draft_id = uuid4()
    now = datetime.now(timezone.utc)

    draft = PlanDraft(
        id=draft_id,
        owner_user_id=user.id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    workspace = DraftWorkspace(
        draft=draft,
        groups=[],
        group_assignments=[],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=True),
    )
    handler.handle.return_value = workspace
    roster_repo.get_by_id.return_value = Roster(
        id=draft.roster_id,
        owner_user_id=user.id,
        name="Class",
        students=[],
        created_at=now,
        updated_at=now,
    )

    result = await _unwrap_dishka(api.redo_draft)(
        draft_id=draft_id,
        handler=handler,
        rosters=roster_repo,
        templates=template_repo,
        user=user,
    )

    assert result.draft.id == draft_id
    assert result.history_status.can_redo is True
    handler.handle.assert_awaited_once_with(draft_id=draft_id, owner_user_id=user.id)
