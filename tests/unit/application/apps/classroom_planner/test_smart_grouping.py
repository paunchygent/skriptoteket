"""Application tests for backend-owned smart grouping."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner.handlers.smart_grouping import (
    NO_CLASSROOM_SIGNAL_MESSAGE,
    NO_HISTORY_BLOCK_MESSAGE,
    RunSmartGroupingHandler,
    SmartGroupingAppliedResult,
    SmartGroupingBlockedResult,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomSeat,
    NormalizedSeatingSnapshot,
    NormalizedSeatPlacement,
    SeatingExportCheckpoint,
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    NormalizedGroupingGroup,
    NormalizedGroupingSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftHistoryStatus,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import DomainError


class _Clock:
    def __init__(self, current_time: datetime) -> None:
        self._current_time = current_time

    def now(self) -> datetime:
        return self._current_time


def _roster(*, owner_user_id, roster_id=None) -> Roster:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return Roster(
        id=roster_id or uuid4(),
        owner_user_id=owner_user_id,
        name="SA24D",
        students=[
            Student(id="ada", display_name="Ada"),
            Student(id="alan", display_name="Alan"),
            Student(id="bea", display_name="Bea"),
            Student(id="cai", display_name="Cai"),
        ],
        created_at=now,
        updated_at=now,
    )


def _template(*, owner_user_id, template_id=None) -> RoomTemplate:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return RoomTemplate(
        id=template_id or uuid4(),
        owner_user_id=owner_user_id,
        name="Sal 101",
        grid_cols=4,
        grid_rows=3,
        seats=[
            Seat(id="seat-1", x=0, y=0),
            Seat(id="seat-2", x=1, y=0),
            Seat(id="seat-3", x=0, y=1),
            Seat(id="seat-4", x=1, y=1),
        ],
        fixtures=[],
        created_at=now,
        updated_at=now,
    )


def _grouping_workspace(
    *,
    owner_user_id,
    roster_id,
    template_id=None,
    revision=4,
    use_history=False,
    grouping_seating_distance_enabled=False,
) -> DraftWorkspace:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return DraftWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING,
            template_id=template_id,
            smart_enabled=True,
            use_history=use_history,
            grouping_seating_distance_enabled=grouping_seating_distance_enabled,
            status=PlanDraftStatus.ACTIVE,
            revision=revision,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        groups=[
            DraftGroup(id="group-a", name="Grupp 1", sort_order=0, name_is_custom=False),
            DraftGroup(id="group-b", name="Grupp 2", sort_order=1, name_is_custom=False),
        ],
        group_assignments=[
            GroupAssignment(student_id="ada", group_id="group-a"),
            GroupAssignment(student_id="alan", group_id="group-a"),
            GroupAssignment(student_id="bea", group_id="group-b"),
            GroupAssignment(student_id="cai", group_id="group-b"),
        ],
        seat_assignments=[],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )


def _seating_workspace(*, owner_user_id, roster_id, template_id) -> DraftWorkspace:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return DraftWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            smart_enabled=True,
            status=PlanDraftStatus.ACTIVE,
            revision=2,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        groups=[],
        group_assignments=[],
        seat_assignments=[
            SeatAssignment(student_id="ada", seat_id="seat-1"),
            SeatAssignment(student_id="alan", seat_id="seat-2"),
            SeatAssignment(student_id="bea", seat_id="seat-3"),
            SeatAssignment(student_id="cai", seat_id="seat-4"),
        ],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _grouping_checkpoint(*, roster_id) -> GroupingExportCheckpoint:
    return GroupingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        assignment_hash="grouping-history-1",
        grouping_snapshot=NormalizedGroupingSnapshot(
            groups=[
                NormalizedGroupingGroup(student_ids=["ada", "alan"]),
                NormalizedGroupingGroup(student_ids=["bea", "cai"]),
            ],
            ungrouped_student_ids=[],
        ),
        created_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )


def _seating_checkpoint(*, roster_id, template_id) -> SeatingExportCheckpoint:
    return SeatingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        template_id=template_id,
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        room_context_hash="room-hash",
        assignment_hash="seat-history-1",
        room_context=SeatingRoomContextSnapshot(
            grid_cols=4,
            grid_rows=3,
            seats=[
                NormalizedRoomSeat(id="seat-1", x=0, y=0),
                NormalizedRoomSeat(id="seat-2", x=1, y=0),
                NormalizedRoomSeat(id="seat-3", x=0, y=1),
                NormalizedRoomSeat(id="seat-4", x=1, y=1),
            ],
            fixtures=[],
        ),
        seating_snapshot=NormalizedSeatingSnapshot(
            placed_assignments=[
                NormalizedSeatPlacement(student_id="ada", seat_id="seat-1"),
                NormalizedSeatPlacement(student_id="alan", seat_id="seat-2"),
                NormalizedSeatPlacement(student_id="bea", seat_id="seat-3"),
                NormalizedSeatPlacement(student_id="cai", seat_id="seat-4"),
            ],
            unplaced_student_ids=[],
        ),
        created_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_run_smart_grouping_blocks_when_use_history_has_no_grouping_checkpoints() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    workspace = _grouping_workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        use_history=True,
    )
    drafts = AsyncMock()
    drafts.get_workspace.return_value = workspace
    handler = RunSmartGroupingHandler(
        uow=AsyncMock(),
        drafts=drafts,
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        grouping_checkpoints=AsyncMock(list_recent_for_roster=AsyncMock(return_value=[])),
        seating_checkpoints=AsyncMock(),
        clock=_Clock(datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)),
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=owner_user_id,
        expected_revision=workspace.draft.revision,
    )

    assert result == SmartGroupingBlockedResult(
        status="blocked",
        reason="no_history",
        message=NO_HISTORY_BLOCK_MESSAGE,
        used_history=False,
        used_live_seating=False,
    )
    drafts.save_workspace.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_smart_grouping_uses_active_seating_draft_before_diversity() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    template = _template(owner_user_id=owner_user_id)
    workspace = _grouping_workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
        grouping_seating_distance_enabled=True,
    )
    seating_workspace = _seating_workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
    )
    persisted_workspace = workspace.model_copy(
        update={
            "draft": workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
                }
            ),
        }
    )
    drafts = AsyncMock()
    drafts.get_workspace.side_effect = [workspace, seating_workspace, persisted_workspace]
    drafts.get_active_by_roster_and_kind.return_value = seating_workspace.draft
    handler = RunSmartGroupingHandler(
        uow=AsyncMock(),
        drafts=drafts,
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        grouping_checkpoints=AsyncMock(list_recent_for_roster=AsyncMock(return_value=[])),
        seating_checkpoints=AsyncMock(),
        clock=_Clock(datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)),
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=owner_user_id,
        expected_revision=workspace.draft.revision,
    )

    assert isinstance(result, SmartGroupingAppliedResult)
    assert result.status == "applied"
    assert result.used_history is False
    assert result.used_live_seating is True
    assert result.message == "Smart gruppindelning klar med stöd från klassens sittschema."
    assignments_by_student = {
        assignment.student_id: assignment.group_id
        for assignment in result.workspace.group_assignments
    }
    assert assignments_by_student["ada"] == assignments_by_student["alan"]
    assert assignments_by_student["bea"] == assignments_by_student["cai"]
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_smart_grouping_falls_back_to_latest_seating_checkpoint() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    template = _template(owner_user_id=owner_user_id)
    workspace = _grouping_workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
        grouping_seating_distance_enabled=True,
    )
    persisted_workspace = workspace.model_copy(
        update={
            "draft": workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
                }
            ),
        }
    )
    drafts = AsyncMock()
    drafts.get_workspace.side_effect = [workspace, persisted_workspace]
    drafts.get_active_by_roster_and_kind.return_value = None
    seating_checkpoints = AsyncMock(
        get_latest_for_roster_and_room_context=AsyncMock(
            return_value=_seating_checkpoint(roster_id=roster.id, template_id=template.id)
        )
    )
    handler = RunSmartGroupingHandler(
        uow=AsyncMock(),
        drafts=drafts,
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        grouping_checkpoints=AsyncMock(list_recent_for_roster=AsyncMock(return_value=[])),
        seating_checkpoints=seating_checkpoints,
        clock=_Clock(datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)),
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=owner_user_id,
        expected_revision=workspace.draft.revision,
    )

    assert isinstance(result, SmartGroupingAppliedResult)
    assert result.used_live_seating is True
    assert result.message == "Smart gruppindelning klar med stöd från klassens sittschema."
    assignments_by_student = {
        assignment.student_id: assignment.group_id
        for assignment in result.workspace.group_assignments
    }
    assert assignments_by_student["ada"] == assignments_by_student["alan"]
    assert assignments_by_student["bea"] == assignments_by_student["cai"]
    seating_checkpoints.get_latest_for_roster_and_room_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_smart_grouping_reports_honest_fallback_without_usable_seating_context() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    template = _template(owner_user_id=owner_user_id)
    workspace = _grouping_workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
        grouping_seating_distance_enabled=True,
    )
    persisted_workspace = workspace.model_copy(
        update={
            "draft": workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
                }
            ),
        }
    )
    drafts = AsyncMock()
    drafts.get_workspace.side_effect = [workspace, persisted_workspace]
    drafts.get_active_by_roster_and_kind.return_value = None
    seating_checkpoints = AsyncMock(
        get_latest_for_roster_and_room_context=AsyncMock(return_value=None)
    )
    handler = RunSmartGroupingHandler(
        uow=AsyncMock(),
        drafts=drafts,
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        grouping_checkpoints=AsyncMock(list_recent_for_roster=AsyncMock(return_value=[])),
        seating_checkpoints=seating_checkpoints,
        clock=_Clock(datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)),
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=owner_user_id,
        expected_revision=workspace.draft.revision,
    )

    assert isinstance(result, SmartGroupingAppliedResult)
    assert result.used_live_seating is False
    assert result.message == f"Smart gruppindelning klar. {NO_CLASSROOM_SIGNAL_MESSAGE}"


@pytest.mark.asyncio
async def test_run_smart_grouping_raises_conflict_for_stale_revision() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    workspace = _grouping_workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        revision=7,
    )
    handler = RunSmartGroupingHandler(
        uow=AsyncMock(),
        drafts=AsyncMock(get_workspace=AsyncMock(return_value=workspace)),
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        grouping_checkpoints=AsyncMock(),
        seating_checkpoints=AsyncMock(),
        clock=_Clock(datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError, match="Draft revision mismatch"):
        await handler.handle(
            draft_id=workspace.draft.id,
            owner_user_id=owner_user_id,
            expected_revision=workspace.draft.revision - 1,
        )
