"""API serialization tests for Klassrumskartan workspace diagnostics.

Purpose:
    Prove the authenticated workspace-load route returns additive
    solver-owned rule diagnostics for marker rehydration after reload.

Relationships:
    - Exercises the thin web serializer around `GetDraftWorkspaceHandler`.
    - Complements application-handler tests that recompute diagnostics.
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
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    SmartRuleDiagnostic,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner as api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _workspace(*, owner_user_id) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    roster_id = uuid4()
    template_id = uuid4()
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            status=PlanDraftStatus.ACTIVE,
            revision=8,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="SA24D",
            students=[Student(id="ada", display_name="Ada")],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=template_id,
            owner_user_id=owner_user_id,
            name="Sal 101",
            seats=[Seat(id="front-left", x=0, y=0)],
            fixtures=[],
            created_at=now,
            updated_at=now,
        ),
        seat_assignments=[SeatAssignment(student_id="ada", seat_id="front-left")],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_draft_workspace_serializes_rehydrated_rule_diagnostics() -> None:
    user = make_user(role=Role.USER)
    workspace = _workspace(owner_user_id=user.id)
    handler = AsyncMock(spec=GetDraftWorkspaceHandler)
    handler.handle.return_value = DraftWorkspaceReadResult(
        workspace=workspace,
        rule_diagnostics=(
            SmartRuleDiagnostic(
                rule_id="near_teacher:ada",
                rule_kind="near_teacher",
                status="satisfied",
                student_ids=("ada",),
                seat_ids=("front-left",),
                reason_code="near_teacher_row_first_rank",
                freshness_key="fresh-1",
            ),
        ),
    )

    result = await _unwrap_dishka(api.get_draft_workspace)(
        draft_id=workspace.draft.id,
        handler=handler,
        user=user,
    )

    assert result.rule_diagnostics[0].rule_id == "near_teacher:ada"
    assert result.rule_diagnostics[0].freshness_key == "fresh-1"
    handler.handle.assert_awaited_once_with(
        draft_id=workspace.draft.id,
        owner_user_id=user.id,
    )
