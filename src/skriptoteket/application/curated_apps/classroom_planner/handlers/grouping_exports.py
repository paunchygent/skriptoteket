"""Grouping export preparation handlers for classroom-planner artifacts.

Purpose:
    Own the grouping-specific export preparation flow that translates the
    active grouping draft into the shared `GroupingExportPresentation` contract
    without taking on workbook/PDF rendering or delivery responsibilities.

Relationships:
    - Reuses classroom-planner draft and roster repositories.
    - Emits application export models from
      `skriptoteket.application.curated_apps.classroom_planner.exports`.
    - Serialized by the grouping-specific API router for PR-0139.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    PreparedGroupingExportContract,
    build_grouping_export_presentation,
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


class PrepareGroupingExportHandler:
    """Prepare a typed grouping export contract for one active grouping draft."""

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
        export_kind: GroupingExportKind,
        paper_size: GroupingExportPaperSize | None,
    ) -> PreparedGroupingExportContract:
        if export_kind is GroupingExportKind.PDF and paper_size is None:
            raise validation_error("PDF-export kräver pappersstorlek.")
        if export_kind is GroupingExportKind.XLSX and paper_size is not None:
            raise validation_error("Excel-export använder inte pappersstorlek.")

        workspace = await self.load_workspace(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        return PreparedGroupingExportContract(
            grouping_draft_id=workspace.draft.id,
            roster_id=workspace.roster.id,
            export_kind=export_kind,
            paper_size=paper_size,
            presentation=build_grouping_export_presentation(workspace=workspace),
        )

    async def load_workspace(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
    ) -> ClassroomPlannerWorkspace:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if workspace is None or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        if workspace.draft.draft_kind != PlanDraftKind.GROUPING:
            raise validation_error("Endast grupputkast kan exporteras från den här exportvägen.")

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
