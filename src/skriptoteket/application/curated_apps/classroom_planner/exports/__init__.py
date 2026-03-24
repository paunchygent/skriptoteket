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
    PosterSceneFixtureVariant,
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
    "PosterSceneFixtureVariant",
    "PosterSceneRoom",
    "PosterSceneSeat",
    "PosterSceneWallSide",
    "SeatingExportJob",
    "SeatingExportJobResult",
    "SeatingExportJobStatus",
    "SeatingExportKind",
    "SeatingExportLayoutId",
    "SeatingExportPaperSize",
    "SeatingExportVaultArtifact",
    "SeatingPosterScene",
    "SeatingPosterRenderRequest",
    "format_student_poster_label",
    "translate_workspace_to_poster_scene",
]
