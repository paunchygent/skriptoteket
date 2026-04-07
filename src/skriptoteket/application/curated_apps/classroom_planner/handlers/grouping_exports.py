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
from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)

from .planner_context import load_hydrated_workspace_for_owner


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
        return self.build_prepared_contract(
            workspace=workspace,
            export_kind=export_kind,
            paper_size=paper_size,
        )

    def build_prepared_contract(
        self,
        *,
        workspace: ClassroomPlannerWorkspace,
        export_kind: GroupingExportKind,
        paper_size: GroupingExportPaperSize | None,
    ) -> PreparedGroupingExportContract:
        """Build the typed grouping export contract from a hydrated workspace."""

        if export_kind is GroupingExportKind.PDF and paper_size is None:
            raise validation_error("PDF-export kräver pappersstorlek.")
        if export_kind is GroupingExportKind.XLSX and paper_size is not None:
            raise validation_error("Excel-export använder inte pappersstorlek.")

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
        return await load_hydrated_workspace_for_owner(
            drafts=self._drafts,
            rosters=self._rosters,
            templates=self._templates,
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            expected_draft_kind=PlanDraftKind.GROUPING,
            wrong_kind_message="Endast grupputkast kan exporteras från den här exportvägen.",
        )
