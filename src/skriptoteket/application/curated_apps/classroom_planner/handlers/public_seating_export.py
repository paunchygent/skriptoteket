"""Stateless public seating export handler for guest Klassrumskartan.

Purpose:
    Render seating exports directly from the browser-owned guest snapshot
    without creating authenticated jobs, Vault artifacts, or owner-scoped
    fallbacks.

Relationships:
    - Consumed only by the public helper route under
      `/api/v1/public/apps/classroom.group-seating-studio/seating/export`.
    - Reuses canonical seating export preparation and local renderers.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    seating_xlsx_view_model,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.public_export_contracts import (
    PublicExportDownload,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
    SeatingXlsxRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol

from .public_smart_run_support import (
    build_public_classroom_planner_workspace,
    materialize_public_smart_workspace,
)
from .seating_exports import PrepareSeatingExportHandler

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MEDIA_TYPE = "application/pdf"


@dataclass(frozen=True, slots=True)
class RunPublicSeatingExportHandler:
    """Render one direct-download seating export from a guest snapshot."""

    prepare: PrepareSeatingExportHandler
    pdf_renderer: SeatingPdfRendererProtocol
    poster_renderer: SeatingPosterRendererProtocol
    xlsx_renderer: SeatingXlsxRendererProtocol
    clock: ClockProtocol

    async def handle(
        self,
        *,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        expected_revision: int,
        export_kind: SeatingExportKind,
        layout_id: SeatingExportLayoutId | None,
        paper_size: SeatingExportPaperSize | None,
    ) -> PublicExportDownload:
        materialized = materialize_public_smart_workspace(
            snapshot=snapshot,
            draft_kind=PlanDraftKind.SEATING,
            now=self.clock.now(),
        )
        _validate_expected_revision(
            expected_revision=expected_revision,
            actual_revision=materialized.draft_payload.revision,
        )
        workspace = build_public_classroom_planner_workspace(materialized=materialized)

        if export_kind is SeatingExportKind.XLSX:
            view_model = seating_xlsx_view_model.build_seating_xlsx_view_model(workspace=workspace)
            return PublicExportDownload(
                filename=view_model.output_filename,
                media_type=_XLSX_MEDIA_TYPE,
                content=self.xlsx_renderer.render(view_model=view_model),
            )

        if layout_id is None:
            raise validation_error("PDF-export kräver layout.")
        if paper_size is None:
            raise validation_error("PDF-export kräver pappersstorlek.")

        prepared = self.prepare.build_prepared_contract(
            workspace=workspace,
            export_kind=SeatingExportKind.PDF,
            layout_id=layout_id,
        )
        rendered = self.poster_renderer.render(
            request=SeatingPosterRenderRequest(
                roster_name=prepared.roster_name,
                template_name=prepared.template_name,
                paper_size=paper_size,
                scene=prepared.poster_scene,
            )
        )
        return PublicExportDownload(
            filename=rendered.output_filename,
            media_type=_PDF_MEDIA_TYPE,
            content=self.pdf_renderer.render(bundle=rendered),
        )


def _validate_expected_revision(*, expected_revision: int, actual_revision: int) -> None:
    if actual_revision == expected_revision:
        return
    raise DomainError(
        code=ErrorCode.CONFLICT,
        message=(f"Draft revision mismatch. Expected {expected_revision}, got {actual_revision}."),
    )
