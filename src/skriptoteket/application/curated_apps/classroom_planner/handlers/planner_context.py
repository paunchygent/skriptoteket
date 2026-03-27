"""Owner-scoped planner context loading for classroom-planner handlers.

This module centralizes the owner checks and workspace hydration shared by
classroom-planner application handlers. It keeps lifecycle/export handlers
focused on behavior while ensuring roster, template, and export-ready workspace
lookups stay owner-scoped and consistent across grouping and seating flows.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    PlanDraftKind,
    RoomTemplate,
    Roster,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)

from .workspace_builders import ensure_active_draft


async def load_roster_and_template_for_owner(
    *,
    rosters: RosterRepositoryProtocol,
    templates: RoomTemplateRepositoryProtocol,
    owner_user_id: UUID,
    roster_id: UUID,
    template_id: UUID | None = None,
) -> tuple[Roster, RoomTemplate | None]:
    """Load owner-scoped roster and optional template for planner lifecycle work."""

    roster = await rosters.get_by_id(roster_id=roster_id)
    if not roster or roster.owner_user_id != owner_user_id:
        raise not_found("Roster", str(roster_id))

    template = None
    if template_id is not None:
        template = await templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

    return roster, template


async def load_hydrated_workspace_for_owner(
    *,
    drafts: PlanDraftRepositoryProtocol,
    rosters: RosterRepositoryProtocol,
    templates: RoomTemplateRepositoryProtocol,
    owner_user_id: UUID,
    draft_id: UUID,
    expected_draft_kind: PlanDraftKind,
    wrong_kind_message: str,
) -> ClassroomPlannerWorkspace:
    """Load and hydrate one owner-scoped planner workspace for export flows."""

    workspace = await drafts.get_workspace(draft_id=draft_id)
    if workspace is None or workspace.draft.owner_user_id != owner_user_id:
        raise not_found("PlanDraft", str(draft_id))
    if workspace.draft.draft_kind != expected_draft_kind:
        raise validation_error(wrong_kind_message)

    ensure_active_draft(draft=workspace.draft)
    roster, template = await load_roster_and_template_for_owner(
        rosters=rosters,
        templates=templates,
        owner_user_id=owner_user_id,
        roster_id=workspace.draft.roster_id,
        template_id=workspace.draft.template_id,
    )
    return ClassroomPlannerWorkspace(
        draft=workspace.draft,
        roster=roster,
        template=template,
        groups=workspace.groups,
        group_assignments=workspace.group_assignments,
        seat_assignments=workspace.seat_assignments,
        student_planning_meta=workspace.student_planning_meta,
        history_status=workspace.history_status,
    )
