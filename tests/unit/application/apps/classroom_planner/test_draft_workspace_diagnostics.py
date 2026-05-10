"""Workspace-load diagnostic rehydration tests for Klassrumskartan.

Purpose:
    Prove that loading a persisted seating workspace recomputes solver-owned
    rule diagnostics from current backend truth instead of relying on a prior
    frontend Smart-run payload.

Relationships:
    - Exercises `GetDraftWorkspaceHandler` with protocol mocks.
    - Complements Smart-run tests that verify diagnostics on run responses.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner.handlers.drafts import (
    DraftWorkspaceReadResult,
    GetDraftWorkspaceHandler,
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
    StudentSeatingPreference,
)


def _workspace(*, owner_user_id, roster_id, template_id) -> DraftWorkspace:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return DraftWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            status=PlanDraftStatus.ACTIVE,
            revision=7,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        seat_assignments=[SeatAssignment(student_id="ada", seat_id="front-left")],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )


def _grouping_workspace(*, owner_user_id, roster_id) -> DraftWorkspace:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return DraftWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING,
            template_id=None,
            status=PlanDraftStatus.ACTIVE,
            revision=2,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _roster(*, owner_user_id, roster_id) -> Roster:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return Roster(
        id=roster_id,
        owner_user_id=owner_user_id,
        name="SA24D",
        students=[Student(id="ada", display_name="Ada")],
        created_at=now,
        updated_at=now,
    )


def _template(*, owner_user_id, template_id) -> RoomTemplate:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return RoomTemplate(
        id=template_id,
        owner_user_id=owner_user_id,
        name="Sal 101",
        grid_cols=4,
        grid_rows=3,
        seats=[Seat(id="front-left", x=0, y=0), Seat(id="back-left", x=0, y=1)],
        fixtures=[
            RoomFixture(
                id="board-1",
                type=RoomFixtureType.WHITEBOARD,
                x=0,
                y=0,
                width=2,
                height=1,
            )
        ],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_draft_workspace_rehydrates_rule_diagnostics() -> None:
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    workspace = _workspace(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
    )
    roster = _roster(owner_user_id=owner_user_id, roster_id=roster_id)
    template = _template(owner_user_id=owner_user_id, template_id=template_id)
    smart_rules = RosterSmartRules(
        roster_id=roster_id,
        revision=3,
        seating_preferences=[StudentSeatingPreference(student_id="ada", near_teacher=True)],
    )
    handler = GetDraftWorkspaceHandler(
        drafts=AsyncMock(get_workspace=AsyncMock(return_value=workspace)),
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(get_by_id=AsyncMock(return_value=template)),
        smart_rules=AsyncMock(get_by_roster_id=AsyncMock(return_value=smart_rules)),
    )

    result = await handler.handle(draft_id=workspace.draft.id, owner_user_id=owner_user_id)

    assert isinstance(result, DraftWorkspaceReadResult)
    assert result.workspace.seat_assignments == workspace.seat_assignments
    assert len(result.rule_diagnostics) == 1
    diagnostic = result.rule_diagnostics[0]
    assert diagnostic.rule_id == "near_teacher:ada"
    assert diagnostic.status == "satisfied"
    assert diagnostic.freshness_key


@pytest.mark.asyncio
async def test_get_draft_workspace_does_not_require_smart_rules_for_grouping() -> None:
    owner_user_id = uuid4()
    roster_id = uuid4()
    workspace = _grouping_workspace(owner_user_id=owner_user_id, roster_id=roster_id)
    roster = _roster(owner_user_id=owner_user_id, roster_id=roster_id)
    smart_rules = AsyncMock()
    handler = GetDraftWorkspaceHandler(
        drafts=AsyncMock(get_workspace=AsyncMock(return_value=workspace)),
        rosters=AsyncMock(get_by_id=AsyncMock(return_value=roster)),
        templates=AsyncMock(),
        smart_rules=smart_rules,
    )

    result = await handler.handle(draft_id=workspace.draft.id, owner_user_id=owner_user_id)

    assert result.rule_diagnostics == ()
    smart_rules.get_by_roster_id.assert_not_called()
