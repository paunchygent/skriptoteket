"""Behavior tests for classroom planner draft lifecycle handlers."""

import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    AbandonDraftHandler,
    ActivateGroupingHistoryDraftHandler,
    ActivateSeatingHistoryDraftHandler,
    CreateGroupingDraftHandler,
    CreateSeatingDraftHandler,
    DeleteHistoricGroupingDraftHandler,
    DeleteHistoricSeatingDraftHandler,
    GetResumableDraftHandler,
    PatchDraftHandler,
    RedoDraftHandler,
    ResolveDraftHandler,
    UndoDraftHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftHistoryStatus,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    ResumablePlanDraft,
    RoomTemplate,
    Roster,
    SeatAssignment,
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
    mock.new_uuid.side_effect = lambda: uuid4()
    return mock


def test_draft_handlers_do_not_depend_on_checkpoint_write_seam() -> None:
    expected_params = {
        UndoDraftHandler: {"uow", "drafts"},
        RedoDraftHandler: {"uow", "drafts"},
        AbandonDraftHandler: {"uow", "drafts", "clock"},
        PatchDraftHandler: {"uow", "drafts", "rosters", "templates", "clock"},
    }

    for handler, expected in expected_params.items():
        assert set(inspect.signature(handler).parameters) == expected


@pytest.mark.asyncio
async def test_resolve_draft_returns_existing_active_draft(
    uow, rosters, templates, drafts, clock, id_generator, now
):
    handler = ResolveDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    existing = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=3,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = existing

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
    )

    assert result.id == existing.id
    assert result.smart_enabled is existing.smart_enabled
    drafts.acquire_roster_kind_lifecycle_lock.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
    )
    drafts.save.assert_awaited_once()
    drafts.save_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_draft_creates_new_draft_when_none_exists(
    uow, rosters, templates, drafts, clock, id_generator
):
    handler = ResolveDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft_id = uuid4()
    id_generator.new_uuid.side_effect = None
    id_generator.new_uuid.return_value = draft_id
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = None

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
    )

    assert result.id == draft_id
    assert result.draft_kind == PlanDraftKind.SEATING
    assert result.status == PlanDraftStatus.ACTIVE
    assert result.smart_enabled is True
    assert result.use_history is True
    assert result.grouping_seating_distance_enabled is True
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_seating_draft_requires_classroom(
    uow, rosters, templates, drafts, clock, id_generator
):
    handler = CreateSeatingDraftHandler(uow, rosters, templates, drafts, clock, id_generator)

    with pytest.raises(DomainError) as error:
        await handler.handle(
            owner_user_id=uuid4(),
            roster_id=uuid4(),
            template_id=None,
        )

    assert error.value.code == ErrorCode.VALIDATION_ERROR
    drafts.save_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_create_seating_draft_supersedes_existing_active_draft(
    uow, rosters, templates, drafts, clock, id_generator, now
):
    handler = CreateSeatingDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    existing = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = existing

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        template_id=template_id,
    )

    assert result.draft_kind == PlanDraftKind.SEATING
    drafts.acquire_roster_kind_lifecycle_lock.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
    )
    drafts.save.assert_awaited_once()
    superseded = drafts.save.await_args.kwargs["draft"]
    assert superseded.id == existing.id
    assert superseded.status == PlanDraftStatus.SUPERSEDED
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_seating_draft_updates_active_draft_in_place_when_room_changes(
    uow, rosters, templates, drafts, clock, id_generator, now
):
    handler = ResolveDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    existing = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = existing
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=existing,
        groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=0)],
        group_assignments=[GroupAssignment(student_id="student-1", group_id="group-1")],
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-1")],
    )

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
    )

    assert result.id == existing.id
    assert result.template_id == template_id
    drafts.mark_status.assert_not_called()
    drafts.save.assert_not_called()
    drafts.save_workspace.assert_awaited_once()
    saved_workspace = drafts.save_workspace.await_args.kwargs["workspace"]
    assert saved_workspace.draft.template_id == template_id
    assert saved_workspace.seat_assignments == []
    assert saved_workspace.group_assignments == [
        GroupAssignment(student_id="student-1", group_id="group-1")
    ]


@pytest.mark.asyncio
async def test_activate_seating_history_draft_supersedes_current_active(uow, drafts, clock, now):
    handler = ActivateSeatingHistoryDraftHandler(uow, drafts, clock)
    owner_id = uuid4()
    roster_id = uuid4()
    target = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.SUPERSEDED,
        revision=1,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    active = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=4,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.side_effect = [target, target]
    drafts.get_active_by_roster_and_kind.return_value = active

    result = await handler.handle(draft_id=target.id, owner_user_id=owner_id)

    assert result.status == PlanDraftStatus.ACTIVE
    drafts.save.assert_awaited()
    assert drafts.save.await_count == 2


@pytest.mark.asyncio
async def test_delete_historic_seating_draft_rejects_active_target(uow, drafts):
    handler = DeleteHistoricSeatingDraftHandler(uow, drafts)
    owner_id = uuid4()
    target = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=4,
        last_opened_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    drafts.get_by_id.return_value = target

    with pytest.raises(DomainError) as error:
        await handler.handle(draft_id=target.id, owner_user_id=owner_id)

    assert error.value.code == ErrorCode.VALIDATION_ERROR
    drafts.delete.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_grouping_draft_updates_active_draft_in_place_when_room_context_changes(
    uow, rosters, templates, drafts, clock, id_generator, now
):
    handler = ResolveDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    existing = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = existing

    drafts.get_workspace.return_value = DraftWorkspace(
        draft=existing,
        groups=[],
        group_assignments=[],
    )

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=template_id,
    )

    assert result.id == existing.id
    assert result.template_id == template_id
    drafts.mark_status.assert_not_called()
    drafts.save.assert_not_called()
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_draft_returns_hydrated_workspace_with_backend_history_status(
    uow, rosters, templates, drafts, clock, now
):
    handler = PatchDraftHandler(uow, drafts, rosters, templates, clock)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft_id = uuid4()
    existing = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    existing_workspace = DraftWorkspace(
        draft=existing,
        groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=0, name_is_custom=False)],
        group_assignments=[],
        seat_assignments=[],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )
    persisted_workspace = DraftWorkspace(
        draft=existing.model_copy(update={"revision": 3, "updated_at": now}),
        groups=[DraftGroup(id="group-1", name="Handledargrupp", sort_order=0, name_is_custom=True)],
        group_assignments=[],
        seat_assignments=[],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )

    drafts.get_workspace.side_effect = [existing_workspace, persisted_workspace]
    rosters.get_by_id.return_value = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="Klass A",
        students=[],
        created_at=now,
        updated_at=now,
    )
    templates.get_by_id.return_value = RoomTemplate(
        id=template_id,
        owner_user_id=owner_id,
        name="Rum 1",
        seats=[],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )

    result = await handler.handle(
        draft_id=draft_id,
        owner_user_id=owner_id,
        expected_revision=2,
        groups=[DraftGroup(id="group-1", name="Handledargrupp", sort_order=0, name_is_custom=True)],
    )

    assert result.draft.revision == 3
    assert result.groups[0].name == "Handledargrupp"
    assert result.history_status.can_undo is True
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_grouping_draft_supersedes_existing_active_grouping(
    uow, rosters, templates, drafts, clock, id_generator, now
):
    handler = CreateGroupingDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    previous_draft = PlanDraft(
        id=uuid4(),
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=4,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    new_draft_id = uuid4()
    id_generator.new_uuid.side_effect = [
        new_draft_id,
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    ]
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    templates.get_by_id.return_value = Mock(spec=RoomTemplate, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = previous_draft

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        template_id=template_id,
    )

    assert result.id == new_draft_id
    assert result.draft_kind == PlanDraftKind.GROUPING
    assert result.template_id == template_id
    drafts.acquire_roster_kind_lifecycle_lock.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
    )
    drafts.save.assert_awaited_once()
    superseded = drafts.save.await_args.kwargs["draft"]
    assert superseded.id == previous_draft.id
    assert superseded.status == PlanDraftStatus.SUPERSEDED
    drafts.save_workspace.assert_awaited_once()
    saved_workspace = drafts.save_workspace.await_args.kwargs["workspace"]
    assert saved_workspace.group_assignments == []
    assert len(saved_workspace.groups) == 4


@pytest.mark.asyncio
async def test_abandon_draft_marks_active_draft_abandoned(uow, drafts, clock, now):
    owner_id = uuid4()
    draft_id = uuid4()
    handler = AbandonDraftHandler(uow, drafts, clock)
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        status=PlanDraftStatus.ACTIVE,
        revision=1,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.return_value = draft

    result = await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert result.status == PlanDraftStatus.ABANDONED
    drafts.acquire_roster_kind_lifecycle_lock.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=draft.roster_id,
        draft_kind=PlanDraftKind.SEATING,
    )
    drafts.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_grouping_draft_allows_missing_template(
    uow, rosters, drafts, clock, id_generator
):
    templates = AsyncMock(spec=RoomTemplateRepositoryProtocol)
    handler = ResolveDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = None

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
    )

    assert result.draft_kind == PlanDraftKind.GROUPING
    assert result.template_id is None
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_seating_draft_allows_missing_template(
    uow, rosters, drafts, clock, id_generator
):
    templates = AsyncMock(spec=RoomTemplateRepositoryProtocol)
    handler = ResolveDraftHandler(uow, rosters, templates, drafts, clock, id_generator)
    owner_id = uuid4()
    roster_id = uuid4()
    rosters.get_by_id.return_value = Mock(spec=Roster, owner_user_id=owner_id)
    drafts.get_active_by_roster_and_kind.return_value = None

    result = await handler.handle(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=None,
    )

    assert result.draft_kind == PlanDraftKind.SEATING
    assert result.template_id is None
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_resumable_draft_returns_repo_payload(drafts, now):
    handler = GetResumableDraftHandler(drafts)
    owner_id = uuid4()
    resumable = ResumablePlanDraft(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_id,
            roster_id=uuid4(),
            draft_kind=PlanDraftKind.SEATING,
            template_id=uuid4(),
            status=PlanDraftStatus.ACTIVE,
            revision=1,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster_name="SA24D",
        template_name="Sal 101",
    )
    drafts.get_latest_resumable.return_value = resumable

    result = await handler.handle(owner_user_id=owner_id)

    assert result == resumable
    drafts.get_latest_resumable.assert_awaited_once_with(owner_user_id=owner_id)


@pytest.mark.asyncio
async def test_undo_draft_allows_active_seating_drafts(uow, drafts, now):
    handler = UndoDraftHandler(uow, drafts)
    owner_id = uuid4()
    draft_id = uuid4()
    draft = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
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
    )
    drafts.get_by_id.return_value = draft
    drafts.undo.return_value = workspace

    result = await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert result == workspace
    drafts.undo.assert_awaited_once_with(draft_id=draft_id)


@pytest.mark.asyncio
async def test_redo_draft_rejects_foreign_drafts_before_mutation(uow, drafts, now):
    handler = RedoDraftHandler(uow, drafts)
    owner_id = uuid4()
    draft_id = uuid4()
    drafts.get_by_id.return_value = PlanDraft(
        id=draft_id,
        owner_user_id=uuid4(),
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(DomainError) as error:
        await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert error.value.code == ErrorCode.NOT_FOUND
    drafts.redo.assert_not_awaited()
    drafts.get_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_activate_grouping_history_draft_promotes_target_and_supersedes_current(
    uow, drafts, clock, now
):
    owner_id = uuid4()
    roster_id = uuid4()
    target_id = uuid4()
    active_id = uuid4()
    handler = ActivateGroupingHistoryDraftHandler(uow, drafts, clock)
    historic = PlanDraft(
        id=target_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.SUPERSEDED,
        revision=3,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    active = PlanDraft(
        id=active_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=6,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.side_effect = [historic, historic]
    drafts.get_active_by_roster_and_kind.return_value = active

    result = await handler.handle(draft_id=target_id, owner_user_id=owner_id)

    assert result.id == target_id
    assert result.status == PlanDraftStatus.ACTIVE
    drafts.acquire_roster_kind_lifecycle_lock.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
    )
    assert drafts.save.await_count == 2
    superseded = drafts.save.await_args_list[0].kwargs["draft"]
    activated = drafts.save.await_args_list[1].kwargs["draft"]
    assert superseded.id == active_id
    assert superseded.status == PlanDraftStatus.SUPERSEDED
    assert activated.id == target_id
    assert activated.status == PlanDraftStatus.ACTIVE


@pytest.mark.asyncio
async def test_delete_historic_grouping_draft_rejects_active_drafts(uow, drafts, now):
    owner_id = uuid4()
    draft_id = uuid4()
    handler = DeleteHistoricGroupingDraftHandler(uow, drafts)
    active = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.return_value = active

    with pytest.raises(DomainError) as error:
        await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    assert error.value.code == ErrorCode.VALIDATION_ERROR
    drafts.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_historic_grouping_draft_deletes_superseded_drafts(uow, drafts, now):
    owner_id = uuid4()
    draft_id = uuid4()
    roster_id = uuid4()
    share_lifecycle = AsyncMock()
    handler = DeleteHistoricGroupingDraftHandler(uow, drafts, share_lifecycle=share_lifecycle)
    historic = PlanDraft(
        id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.SUPERSEDED,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    drafts.get_by_id.side_effect = [historic, historic]

    await handler.handle(draft_id=draft_id, owner_user_id=owner_id)

    drafts.acquire_roster_kind_lifecycle_lock.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
    )
    share_lifecycle.revoke_for_draft_delete.assert_awaited_once_with(
        owner_user_id=owner_id,
        draft_id=draft_id,
        draft_kind=PlanDraftKind.GROUPING,
    )
    drafts.delete.assert_awaited_once_with(draft_id=draft_id)
