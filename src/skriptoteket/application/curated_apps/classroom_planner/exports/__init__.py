"""Export models and translators for classroom-planner artifact seams.

Purpose:
    Keep export-ready projections for Klassrumskartan outside the planner
    domain core while still sharing the same draft, roster, and room-template
    sources of truth.

Relationships:
    - Used by seating export handlers in
      `skriptoteket.application.curated_apps.classroom_planner.handlers`.
    - Serialized by the classroom-planner API export-contract module under
      `skriptoteket.web.api.v1`.
    - Intended to feed later export-specific HTML/CSS rendering without
      assuming planner DOM reuse or direct PDF primitives.
"""

from .grouping_jobs import (
    GroupingExportJob,
    GroupingExportJobResult,
    GroupingExportJobStatus,
    GroupingExportVaultArtifact,
)
from .grouping_pdf_view_model import (
    GroupingPdfCard,
    GroupingPdfCardPair,
    GroupingPdfMemberRow,
    GroupingPdfViewModel,
    build_grouping_pdf_view_model,
)
from .grouping_presentation import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    GroupingPresentationGroup,
    GroupingPresentationMember,
    PreparedGroupingExportContract,
    build_grouping_export_presentation,
)
from .grouping_xlsx_view_model import (
    GroupingXlsxEditRow,
    GroupingXlsxRegistryRow,
    GroupingXlsxWorkbookViewModel,
    build_grouping_xlsx_view_model,
)
from .jobs import (
    SeatingExportJob,
    SeatingExportJobResult,
    SeatingExportJobStatus,
    SeatingExportPaperSize,
    SeatingExportVaultArtifact,
)
from .models import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneFixtureTone,
    PosterSceneFixtureVariant,
    PosterSceneLabelOrientation,
    PosterSceneRoom,
    PosterSceneSeat,
    PosterSceneWallSide,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from .rendering import RenderedSeatingPosterBundle, SeatingPosterRenderRequest
from .translator import format_student_poster_label, translate_workspace_to_poster_scene

__all__ = [
    "PreparedSeatingExportContract",
    "RenderedSeatingPosterBundle",
    "PosterSceneFixture",
    "PosterSceneFixtureKind",
    "PosterSceneFixturePlacement",
    "PosterSceneFixtureTone",
    "PosterSceneFixtureVariant",
    "PosterSceneLabelOrientation",
    "PosterSceneRoom",
    "PosterSceneSeat",
    "PosterSceneWallSide",
    "GroupingExportJob",
    "GroupingExportJobResult",
    "GroupingExportJobStatus",
    "GroupingExportKind",
    "GroupingExportPaperSize",
    "GroupingExportPresentation",
    "GroupingExportVaultArtifact",
    "GroupingPdfCard",
    "GroupingPdfCardPair",
    "GroupingPdfMemberRow",
    "GroupingPdfViewModel",
    "GroupingXlsxEditRow",
    "GroupingXlsxRegistryRow",
    "GroupingXlsxWorkbookViewModel",
    "GroupingPresentationGroup",
    "GroupingPresentationMember",
    "SeatingExportJob",
    "SeatingExportJobResult",
    "SeatingExportJobStatus",
    "SeatingExportKind",
    "SeatingExportLayoutId",
    "SeatingExportPaperSize",
    "SeatingExportVaultArtifact",
    "SeatingPosterScene",
    "SeatingPosterRenderRequest",
    "PreparedGroupingExportContract",
    "build_grouping_export_presentation",
    "build_grouping_pdf_view_model",
    "build_grouping_xlsx_view_model",
    "format_student_poster_label",
    "translate_workspace_to_poster_scene",
]
