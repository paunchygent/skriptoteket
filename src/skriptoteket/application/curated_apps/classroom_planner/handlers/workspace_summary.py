"""Class-workspace read models for the classroom planner.

This module builds the compact class-first workspace summary used by the
landing-to-class-workspace flow. It keeps read-model orchestration separate
from mutable draft lifecycle handlers while reusing the active `draft_kind`
contract and roster ownership checks.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    ClassWorkspaceRosterSummary,
    ClassWorkspaceSummary,
    PlanDraftKind,
    TaskEntryOption,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RosterRepositoryProtocol,
)


def _default_task_entry_options() -> list[TaskEntryOption]:
    """Return the approved task-entry rules for the class workspace."""

    return [
        TaskEntryOption(
            draft_kind=PlanDraftKind.GROUPING,
            classroom_selection_mode=ClassroomSelectionMode.OPTIONAL,
        ),
        TaskEntryOption(
            draft_kind=PlanDraftKind.SEATING,
            classroom_selection_mode=ClassroomSelectionMode.REQUIRED,
        ),
    ]


class GetClassWorkspaceSummaryHandler:
    """Load the compact class-first workspace summary for one roster/class."""

    def __init__(
        self,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> None:
        self._rosters = rosters
        self._drafts = drafts

    async def handle(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
    ) -> ClassWorkspaceSummary:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))

        draft_summary = await self._drafts.get_class_workspace_draft_summary(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
        )

        return ClassWorkspaceSummary(
            roster=ClassWorkspaceRosterSummary(
                id=roster.id,
                name=roster.name,
                student_count=len(roster.students),
            ),
            task_entry_options=_default_task_entry_options(),
            active_grouping_draft=draft_summary.active_grouping_draft,
            active_seating_draft=draft_summary.active_seating_draft,
            grouping_history=draft_summary.grouping_history,
            seating_history=draft_summary.seating_history,
        )
