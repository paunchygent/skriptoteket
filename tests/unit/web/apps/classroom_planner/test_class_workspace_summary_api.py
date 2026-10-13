"""Unit coverage for the class-workspace summary API endpoint.

This module verifies that the bespoke classroom-planner summary route maps the
application read model into the compact public DTO expected by the SPA.
"""

from datetime import datetime, timezone
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
from tests.fixtures.identity_fixtures import make_user


class _StubSummaryHandler(GetClassWorkspaceSummaryHandler):
    """A handler double with the production handler's own signature.

    The route is called directly below, so mypy checks this double and
    every argument against the production route and handler types.
    """

    def __init__(self, result: ClassWorkspaceSummary) -> None:
        self._result = result
        self.calls: list[dict[str, UUID]] = []

    async def handle(self, *, owner_user_id: UUID, roster_id: UUID) -> ClassWorkspaceSummary:
        self.calls.append({"owner_user_id": owner_user_id, "roster_id": roster_id})
        return self._result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_class_workspace_summary_returns_serialized_payload():
    user = make_user(role=Role.USER)
    roster_id = uuid4()
    now = datetime.now(timezone.utc)
    grouping_draft_id = uuid4()

    handler = _StubSummaryHandler(
        ClassWorkspaceSummary(
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
                    classroom_selection_mode=ClassroomSelectionMode.OPTIONAL,
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
    )

    result = await api.get_class_workspace_summary(
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
    assert result.task_entry_options[1].classroom_selection_mode == ClassroomSelectionMode.OPTIONAL
    assert handler.calls == [{"roster_id": roster_id, "owner_user_id": user.id}]
