"""Unit coverage for the class-workspace summary API endpoint.

This module verifies that the bespoke classroom-planner summary route maps the
application read model into the compact public DTO expected by the SPA.
"""

from datetime import datetime, timezone
from typing import Protocol, TypeGuard
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import GetClassWorkspaceSummaryHandler
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    ClassWorkspaceRosterSummary,
    ClassWorkspaceSummary,
    PlanDraftKind,
    PlanDraftStatus,
    PlanDraftSummary,
    TaskEntryOption,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner as api
from skriptoteket.web.api.v1.apps_classroom_planner_summary import (
    ClassWorkspaceSummaryDto,
)
from tests.fixtures.identity_fixtures import make_user


class _ClassWorkspaceSummaryEndpoint(Protocol):
    """Describe the unwrapped async handler signature used in this test."""

    async def __call__(
        self,
        *,
        roster_id: UUID,
        handler: GetClassWorkspaceSummaryHandler,
        user: object,
    ) -> ClassWorkspaceSummaryDto: ...


def _is_class_workspace_summary_endpoint(
    value: object,
) -> TypeGuard[_ClassWorkspaceSummaryEndpoint]:
    """Tell mypy when an unwrapped Dishka target matches the async handler shape."""

    return callable(value)


def _unwrap_dishka(fn: object) -> _ClassWorkspaceSummaryEndpoint:
    """Extract original function from Dishka-wrapped handlers."""

    unwrapped = getattr(fn, "__dishka_orig_func__", None)
    assert _is_class_workspace_summary_endpoint(unwrapped)
    return unwrapped


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_class_workspace_summary_returns_serialized_payload():
    user = make_user(role=Role.USER)
    roster_id = uuid4()
    handler = AsyncMock(spec=GetClassWorkspaceSummaryHandler)
    now = datetime.now(timezone.utc)
    grouping_draft_id = uuid4()

    handler.handle.return_value = ClassWorkspaceSummary(
        roster=ClassWorkspaceRosterSummary(
            id=roster_id,
            name="SA24D",
            student_count=28,
        ),
        task_entry_options=[
            TaskEntryOption(
                draft_kind=PlanDraftKind.GROUPING,
                classroom_selection_mode=ClassroomSelectionMode.OPTIONAL,
            ),
            TaskEntryOption(
                draft_kind=PlanDraftKind.SEATING,
                classroom_selection_mode=ClassroomSelectionMode.REQUIRED,
            ),
        ],
        active_grouping_draft=PlanDraftSummary(
            id=grouping_draft_id,
            draft_kind=PlanDraftKind.GROUPING,
            template_id=None,
            template_name=None,
            status=PlanDraftStatus.ACTIVE,
            revision=3,
            last_opened_at=now,
            updated_at=now,
        ),
        active_seating_draft=None,
        grouping_history=[],
        seating_history=[],
    )

    endpoint = _unwrap_dishka(api.get_class_workspace_summary)
    result = await endpoint(
        roster_id=roster_id,
        handler=handler,
        user=user,
    )

    assert result.roster.id == roster_id
    assert result.roster.name == "SA24D"
    assert result.roster.student_count == 28
    assert result.active_grouping_draft is not None
    assert result.active_grouping_draft.id == grouping_draft_id
    assert result.active_grouping_draft.status == PlanDraftStatus.ACTIVE
    assert result.task_entry_options[0].classroom_selection_mode == ClassroomSelectionMode.OPTIONAL
    assert result.task_entry_options[1].classroom_selection_mode == ClassroomSelectionMode.REQUIRED
    handler.handle.assert_awaited_once_with(roster_id=roster_id, owner_user_id=user.id)
