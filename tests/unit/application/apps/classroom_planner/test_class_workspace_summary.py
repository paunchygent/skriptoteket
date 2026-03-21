"""Unit coverage for the class-workspace summary application handler.

This module verifies that the class-workspace read-model handler enforces
roster ownership and returns task-separated summary data for the SPA contract.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import GetClassWorkspaceSummaryHandler
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    ClassWorkspaceDraftSummary,
    PlanDraftKind,
    PlanDraftStatus,
    PlanDraftSummary,
    Roster,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RosterRepositoryProtocol,
)


@pytest.fixture
def rosters() -> AsyncMock:
    return AsyncMock(spec=RosterRepositoryProtocol)


@pytest.fixture
def drafts() -> AsyncMock:
    return AsyncMock(spec=PlanDraftRepositoryProtocol)


@pytest.fixture
def now() -> datetime:
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_get_class_workspace_summary_returns_task_separated_payload(
    rosters: AsyncMock,
    drafts: AsyncMock,
    now: datetime,
) -> None:
    owner_id = uuid4()
    roster_id = uuid4()
    handler = GetClassWorkspaceSummaryHandler(rosters=rosters, drafts=drafts)

    rosters.get_by_id.return_value = Roster(
        id=roster_id,
        owner_user_id=owner_id,
        name="SA24D",
        students=[
            Student(id="s1", display_name="Ada"),
            Student(id="s2", display_name="Bo"),
        ],
        created_at=now,
        updated_at=now,
    )
    drafts.get_class_workspace_draft_summary.return_value = ClassWorkspaceDraftSummary(
        active_grouping_draft=PlanDraftSummary(
            id=uuid4(),
            draft_kind=PlanDraftKind.GROUPING,
            template_id=None,
            template_name=None,
            status=PlanDraftStatus.ACTIVE,
            revision=2,
            last_opened_at=now,
            updated_at=now,
        ),
        active_seating_draft=None,
        grouping_history=[],
        seating_history=[
            PlanDraftSummary(
                id=uuid4(),
                draft_kind=PlanDraftKind.SEATING,
                template_id=uuid4(),
                template_name="Sal 101",
                status=PlanDraftStatus.SUPERSEDED,
                revision=5,
                last_opened_at=now,
                updated_at=now,
            )
        ],
    )

    result = await handler.handle(owner_user_id=owner_id, roster_id=roster_id)

    assert result.roster.id == roster_id
    assert result.roster.name == "SA24D"
    assert result.roster.student_count == 2
    assert result.active_grouping_draft is not None
    assert result.active_grouping_draft.draft_kind == PlanDraftKind.GROUPING
    assert result.active_seating_draft is None
    assert len(result.seating_history) == 1
    assert [option.draft_kind for option in result.task_entry_options] == [
        PlanDraftKind.GROUPING,
        PlanDraftKind.SEATING,
    ]
    assert result.task_entry_options[0].classroom_selection_mode == ClassroomSelectionMode.OPTIONAL
    assert result.task_entry_options[1].classroom_selection_mode == ClassroomSelectionMode.REQUIRED
    drafts.get_class_workspace_draft_summary.assert_awaited_once_with(
        owner_user_id=owner_id,
        roster_id=roster_id,
    )


@pytest.mark.asyncio
async def test_get_class_workspace_summary_rejects_missing_roster(
    rosters: AsyncMock,
    drafts: AsyncMock,
) -> None:
    owner_id = uuid4()
    roster_id = uuid4()
    handler = GetClassWorkspaceSummaryHandler(rosters=rosters, drafts=drafts)
    rosters.get_by_id.return_value = None

    with pytest.raises(DomainError) as exc:
        await handler.handle(owner_user_id=owner_id, roster_id=roster_id)

    assert exc.value.code == ErrorCode.NOT_FOUND
    drafts.get_class_workspace_draft_summary.assert_not_called()
