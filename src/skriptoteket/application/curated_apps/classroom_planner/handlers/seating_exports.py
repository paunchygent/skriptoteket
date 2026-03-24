"""Seating export preparation handlers for classroom-planner artifacts.

Purpose:
    Own the seating-specific export preparation flow that translates the active
    seating draft into a standalone poster-scene contract without taking on
    final HTML/CSS rendering or PDF delivery responsibilities.

Relationships:
    - Reuses classroom-planner draft, roster, and room-template repositories.
    - Emits application export models from
      `skriptoteket.application.curated_apps.classroom_planner.exports`.
    - Serialized by the seating-specific API router for PR-0118.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    translate_workspace_to_poster_scene,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    PlanDraftKind,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)

from .workspace_builders import ensure_active_draft


class PrepareSeatingExportHandler:
    """Prepare a typed seating export contract for one active seating draft."""

    def __init__(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
    ) -> None:
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        export_kind: SeatingExportKind,
        layout_id: SeatingExportLayoutId,
    ) -> PreparedSeatingExportContract:
        if export_kind != SeatingExportKind.PDF:
            raise validation_error("Det här exportformatet stöds inte ännu.")

        workspace = await self._load_workspace(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        if workspace.template is None:
            raise validation_error("Välj klassrum innan du exporterar sittschemat.")

        return PreparedSeatingExportContract(
            seating_draft_id=workspace.draft.id,
            roster_id=workspace.roster.id,
            roster_name=workspace.roster.name,
            template_id=workspace.template.id,
            template_name=workspace.template.name,
            export_kind=export_kind,
            layout_id=layout_id,
            poster_scene=translate_workspace_to_poster_scene(workspace=workspace),
        )

    async def _load_workspace(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
    ) -> ClassroomPlannerWorkspace:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if workspace is None or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        if workspace.draft.draft_kind != PlanDraftKind.SEATING:
            raise validation_error("Endast sittscheman kan exporteras från den här exportvägen.")

        ensure_active_draft(draft=workspace.draft)

        roster = await self._rosters.get_by_id(roster_id=workspace.draft.roster_id)
        if roster is None or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(workspace.draft.roster_id))

        template = None
        if workspace.draft.template_id is not None:
            template = await self._templates.get_by_id(template_id=workspace.draft.template_id)
            if template is None or template.owner_user_id != owner_user_id:
                raise not_found("RoomTemplate", str(workspace.draft.template_id))

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
