"""PDF renderer for immutable Klassrumskartan share artifacts.

Purpose:
    Convert stored share artifacts into teacher-downloadable PDFs by delegating
    to the export-owned print renderers rather than reusing responsive
    share-page HTML as a print source.

Relationships:
    - Implements `ClassroomPlannerSharePdfRendererProtocol`.
    - Consumed by the anonymous share read route.
    - Reconstructs renderer-independent payloads persisted on share artifacts.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportPresentation,
    PreparedSeatingExportContract,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    build_grouping_pdf_view_model,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    JsonObject,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingPdfRendererProtocol,
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
)
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerSharePdfRendererProtocol,
)

_PDF_CACHE_MAX_ITEMS = 32
type _PdfCacheKey = tuple[str, str, str]


class ExportBackedClassroomPlannerSharePdfRenderer(ClassroomPlannerSharePdfRendererProtocol):
    """Render share PDFs through canonical export PDF renderer boundaries."""

    def __init__(
        self,
        *,
        seating_poster_renderer: SeatingPosterRendererProtocol,
        seating_pdf_renderer: SeatingPdfRendererProtocol,
        grouping_pdf_renderer: GroupingPdfRendererProtocol,
    ) -> None:
        self._seating_poster_renderer = seating_poster_renderer
        self._seating_pdf_renderer = seating_pdf_renderer
        self._grouping_pdf_renderer = grouping_pdf_renderer
        self._cache = _SharePdfCache(max_items=_PDF_CACHE_MAX_ITEMS)

    def render(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        cached = self._cache.get(artifact)
        if cached is not None:
            return cached

        if artifact.draft_kind is PlanDraftKind.SEATING:
            pdf_bytes = self._render_seating(artifact=artifact)
        else:
            pdf_bytes = self._render_grouping(artifact=artifact)
        self._cache.set(artifact, pdf_bytes)
        return pdf_bytes

    def _render_seating(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        prepared = PreparedSeatingExportContract.model_validate(_presentation_payload(artifact))
        poster_bundle = self._seating_poster_renderer.render(
            request=SeatingPosterRenderRequest(
                roster_name=prepared.roster_name,
                template_name=prepared.template_name,
                paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
                scene=prepared.poster_scene,
            )
        )
        return self._seating_pdf_renderer.render(bundle=poster_bundle)

    def _render_grouping(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        presentation = GroupingExportPresentation.model_validate(_presentation_payload(artifact))
        view_model = build_grouping_pdf_view_model(
            presentation=presentation,
            generated_at=artifact.created_at,
        )
        return self._grouping_pdf_renderer.render(view_model=view_model)


def _presentation_payload(artifact: ClassroomPlannerShareArtifact) -> JsonObject:
    """Return the stored canonical payload or fail closed for corrupt artifacts."""

    if artifact.presentation_payload is None:
        raise ValueError("Share artifact is missing presentation payload.")
    return artifact.presentation_payload


class _SharePdfCache:
    """Bounded per-process cache for immutable share PDF bytes."""

    def __init__(self, *, max_items: int) -> None:
        self._max_items = max_items
        self._items: OrderedDict[_PdfCacheKey, bytes] = OrderedDict()
        self._lock = Lock()

    def get(self, artifact: ClassroomPlannerShareArtifact) -> bytes | None:
        key = _cache_key(artifact)
        with self._lock:
            pdf_bytes = self._items.get(key)
            if pdf_bytes is None:
                return None
            self._items.move_to_end(key)
            return pdf_bytes

    def set(self, artifact: ClassroomPlannerShareArtifact, pdf_bytes: bytes) -> None:
        key = _cache_key(artifact)
        with self._lock:
            self._items[key] = pdf_bytes
            self._items.move_to_end(key)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)


def _cache_key(artifact: ClassroomPlannerShareArtifact) -> _PdfCacheKey:
    return (str(artifact.id), artifact.content_hash, artifact.created_at.isoformat())
