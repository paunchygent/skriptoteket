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
from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)

from .planner_context import load_hydrated_workspace_for_owner


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

        workspace = await self.load_workspace(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        return self.build_prepared_contract(
            workspace=workspace,
            export_kind=export_kind,
            layout_id=layout_id,
        )

    def build_prepared_contract(
        self,
        *,
        workspace: ClassroomPlannerWorkspace,
        export_kind: SeatingExportKind,
        layout_id: SeatingExportLayoutId,
    ) -> PreparedSeatingExportContract:
        """Build the typed seating export contract from a hydrated workspace."""

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
            expected_draft_kind=PlanDraftKind.SEATING,
            wrong_kind_message="Endast sittscheman kan exporteras från den här exportvägen.",
        )
