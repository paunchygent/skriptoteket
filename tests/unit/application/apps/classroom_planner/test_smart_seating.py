"""Application tests for backend-owned smart seating."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner.handlers.smart_seating import (
    NO_HISTORY_BLOCK_MESSAGE,
    RunSmartSeatingHandler,
    SmartSeatingAppliedResult,
    SmartSeatingBlockedResult,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomSeat,
    NormalizedSeatingSnapshot,
    NormalizedSeatPlacement,
    SeatingExportCheckpoint,
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftHistoryStatus,
    DraftWorkspace,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomFixture,
    RoomFixtureType,
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
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return Roster(
        id=roster_id or uuid4(),
        owner_user_id=owner_user_id,
        name="SA24D",
        students=[
            Student(id="ada", display_name="Ada"),
            Student(id="alan", display_name="Alan"),
        ],
        created_at=now,
        updated_at=now,
    )


def _template(*, owner_user_id, template_id=None) -> RoomTemplate:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return RoomTemplate(
        id=template_id or uuid4(),
        owner_user_id=owner_user_id,
        name="Sal 101",
        grid_cols=4,
        grid_rows=3,
        seats=[
            Seat(id="front-left", x=0, y=0),
            Seat(id="front-right", x=1, y=0),
            Seat(id="back-left", x=0, y=1),
            Seat(id="back-right", x=1, y=1),
        ],
        fixtures=[
            RoomFixture(
                id="board-1",
                type=RoomFixtureType.WHITEBOARD,
                x=0,
                y=0,
                width=1,
                height=1,
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _workspace(
    *, owner_user_id, roster_id, template_id, revision=4, use_history=False
) -> DraftWorkspace:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return DraftWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            smart_enabled=True,
            use_history=use_history,
            status=PlanDraftStatus.ACTIVE,
            revision=revision,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        groups=[],
        group_assignments=[],
        seat_assignments=[
            SeatAssignment(student_id="ada", seat_id="front-left"),
            SeatAssignment(student_id="alan", seat_id="front-right"),
        ],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )


def _checkpoint(*, roster_id) -> SeatingExportCheckpoint:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return SeatingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        template_id=uuid4(),
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        room_context_hash="room-hash",
        assignment_hash="assignment-hash",
        room_context=SeatingRoomContextSnapshot(
            grid_cols=4,
            grid_rows=3,
            seats=[
                NormalizedRoomSeat(id="front-left", x=0, y=0),
                NormalizedRoomSeat(id="front-right", x=1, y=0),
                NormalizedRoomSeat(id="back-left", x=0, y=1),
                NormalizedRoomSeat(id="back-right", x=1, y=1),
            ],
            fixtures=[
                {
                    "id": "board-1",
                    "type": "whiteboard",
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                    "label": None,
                }
            ],
        ),
        seating_snapshot=NormalizedSeatingSnapshot(
            placed_assignments=[
                NormalizedSeatPlacement(student_id="ada", seat_id="front-left"),
                NormalizedSeatPlacement(student_id="alan", seat_id="back-right"),
            ],
            unplaced_student_ids=[],
        ),
        created_at=now,
    )


@pytest.mark.asyncio
async def test_run_smart_seating_blocks_when_use_history_has_no_eligible_checkpoints() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    template = _template(owner_user_id=owner_user_id)
    workspace = _workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
        use_history=True,
    )
    drafts = AsyncMock()
    drafts.get_workspace.return_value = workspace
    handler = RunSmartSeatingHandler(
        uow=AsyncMock(),
        drafts=drafts,
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        checkpoints=AsyncMock(list_recent_for_roster_and_room_context=AsyncMock(return_value=[])),
        clock=_Clock(datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)),
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=owner_user_id,
        expected_revision=workspace.draft.revision,
    )

    assert result == SmartSeatingBlockedResult(
        status="blocked",
        reason="no_history",
        message=NO_HISTORY_BLOCK_MESSAGE,
        used_history=False,
    )
    drafts.save_workspace.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_smart_seating_loads_recent_checkpoint_window_and_persists_result() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    template = _template(owner_user_id=owner_user_id)
    workspace = _workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
        use_history=True,
    )
    persisted_workspace = workspace.model_copy(
        update={
            "draft": workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
                }
            ),
            "seat_assignments": [
                SeatAssignment(student_id="ada", seat_id="front-right"),
                SeatAssignment(student_id="alan", seat_id="back-left"),
            ],
        }
    )
    drafts = AsyncMock()
    drafts.get_workspace.side_effect = [workspace, persisted_workspace]
    checkpoints = AsyncMock()
    checkpoints.list_recent_for_roster_and_room_context.return_value = [
        _checkpoint(roster_id=roster.id)
    ]
    handler = RunSmartSeatingHandler(
        uow=AsyncMock(),
        drafts=drafts,
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        checkpoints=checkpoints,
        clock=_Clock(datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)),
    )

    result = await handler.handle(
        draft_id=workspace.draft.id,
        owner_user_id=owner_user_id,
        expected_revision=workspace.draft.revision,
    )

    assert isinstance(result, SmartSeatingAppliedResult)
    assert result.status == "applied"
    assert result.used_history is True
    assert result.workspace.draft.revision == workspace.draft.revision + 1
    assert result.workspace.seat_assignments == persisted_workspace.seat_assignments
    checkpoints.list_recent_for_roster_and_room_context.assert_awaited_once()
    drafts.save_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_smart_seating_raises_conflict_for_stale_revision() -> None:
    owner_user_id = uuid4()
    roster = _roster(owner_user_id=owner_user_id)
    template = _template(owner_user_id=owner_user_id)
    workspace = _workspace(
        owner_user_id=owner_user_id,
        roster_id=roster.id,
        template_id=template.id,
        revision=7,
    )
    handler = RunSmartSeatingHandler(
        uow=AsyncMock(),
        drafts=AsyncMock(get_workspace=AsyncMock(return_value=workspace)),
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(
            get_by_roster_id=AsyncMock(return_value=RosterSmartRules(roster_id=roster.id))
        ),
        checkpoints=AsyncMock(),
        clock=_Clock(datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError, match="Draft revision mismatch"):
        await handler.handle(
            draft_id=workspace.draft.id,
            owner_user_id=owner_user_id,
            expected_revision=workspace.draft.revision - 1,
        )
