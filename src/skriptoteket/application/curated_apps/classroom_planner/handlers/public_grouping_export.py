"""Stateless public grouping export handler for guest Klassrumskartan.

Purpose:
    Render grouping exports directly from the browser-owned guest snapshot
    without creating authenticated jobs, Vault artifacts, or owner-scoped
    fallbacks.

Relationships:
    - Consumed only by the public helper route under
      `/api/v1/public/apps/classroom.group-seating-studio/grouping/export`.
    - Reuses canonical grouping export preparation and local renderers.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    build_grouping_pdf_view_model,
    build_grouping_xlsx_view_model,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.public_export_contracts import (
    PublicExportDownload,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    PlanDraftKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingPdfRendererProtocol,
    GroupingXlsxRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol

from .grouping_exports import PrepareGroupingExportHandler
from .public_smart_run_support import (
    build_public_classroom_planner_workspace,
    materialize_public_smart_workspace,
)

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MEDIA_TYPE = "application/pdf"


@dataclass(frozen=True, slots=True)
class RunPublicGroupingExportHandler:
    """Render one direct-download grouping export from a guest snapshot."""

    prepare: PrepareGroupingExportHandler
    pdf_renderer: GroupingPdfRendererProtocol
    xlsx_renderer: GroupingXlsxRendererProtocol
    clock: ClockProtocol

    async def handle(
        self,
        *,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        expected_revision: int,
        export_kind: GroupingExportKind,
        paper_size: GroupingExportPaperSize | None,
    ) -> PublicExportDownload:
        materialized = materialize_public_smart_workspace(
            snapshot=snapshot,
            draft_kind=PlanDraftKind.GROUPING,
            now=self.clock.now(),
        )
        _validate_expected_revision(
            expected_revision=expected_revision,
            actual_revision=materialized.draft_payload.revision,
        )
        workspace = build_public_classroom_planner_workspace(materialized=materialized)

        if export_kind is GroupingExportKind.XLSX:
            prepared = self.prepare.build_prepared_contract(
                workspace=workspace,
                export_kind=GroupingExportKind.XLSX,
                paper_size=None,
            )
            xlsx_view_model = build_grouping_xlsx_view_model(
                presentation=prepared.presentation,
                generated_at=self.clock.now(),
                unassigned_student_names=_unassigned_student_names(workspace),
            )
            return PublicExportDownload(
                filename=xlsx_view_model.output_filename,
                media_type=_XLSX_MEDIA_TYPE,
                content=self.xlsx_renderer.render(view_model=xlsx_view_model),
            )

        prepared = self.prepare.build_prepared_contract(
            workspace=workspace,
            export_kind=GroupingExportKind.PDF,
            paper_size=paper_size,
        )
        pdf_view_model = build_grouping_pdf_view_model(
            presentation=prepared.presentation,
            generated_at=self.clock.now(),
        )
        return PublicExportDownload(
            filename=pdf_view_model.output_filename,
            media_type=_PDF_MEDIA_TYPE,
            content=self.pdf_renderer.render(view_model=pdf_view_model),
        )


def _validate_expected_revision(*, expected_revision: int, actual_revision: int) -> None:
    if actual_revision == expected_revision:
        return
    raise DomainError(
        code=ErrorCode.CONFLICT,
        message=(f"Draft revision mismatch. Expected {expected_revision}, got {actual_revision}."),
    )


def _unassigned_student_names(workspace: ClassroomPlannerWorkspace) -> tuple[str, ...]:
    """Collect students who are still ungrouped in the current workspace."""

    assigned_student_ids = {assignment.student_id for assignment in workspace.group_assignments}
    return tuple(
        sorted(
            (
                student.display_name
                for student in workspace.roster.students
                if student.id not in assigned_student_ids
            ),
            key=lambda name: name.casefold(),
        )
    )
