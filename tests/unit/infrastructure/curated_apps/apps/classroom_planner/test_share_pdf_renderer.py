"""Unit tests for Klassrumskartan share-page PDF rendering.

Purpose:
    Prove share PDF downloads reuse the canonical export-owned print renderers
    instead of converting responsive public share-page HTML.

Relationships:
    - Exercises `ExportBackedClassroomPlannerSharePdfRenderer`.
    - Complements public share route tests for token and attachment behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    GroupingPresentationGroup,
    GroupingPresentationMember,
    PosterSceneRoom,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    RenderedSeatingPosterBundle,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
    SeatingPosterScene,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    JsonObject,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_pdf_renderer import (
    ExportBackedClassroomPlannerSharePdfRenderer,
)
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingPdfRendererProtocol,
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
)


@pytest.mark.unit
def test_share_pdf_renderer_uses_seating_poster_and_pdf_renderers() -> None:
    prepared = _prepared_seating()
    poster_bundle = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content="<html>poster</html>",
        css_filename="poster.css",
        css_content="body { color: black; }",
        output_filename="klass-7a-a3.pdf",
    )
    seating_poster_renderer = MagicMock(spec=SeatingPosterRendererProtocol)
    seating_poster_renderer.render.return_value = poster_bundle
    seating_pdf_renderer = MagicMock(spec=SeatingPdfRendererProtocol)
    seating_pdf_renderer.render.return_value = b"%PDF-seating"
    grouping_pdf_renderer = MagicMock(spec=GroupingPdfRendererProtocol)

    pdf_bytes = _renderer(
        seating_poster_renderer=seating_poster_renderer,
        seating_pdf_renderer=seating_pdf_renderer,
        grouping_pdf_renderer=grouping_pdf_renderer,
    ).render(
        artifact=_artifact(
            draft_kind=PlanDraftKind.SEATING,
            presentation_payload=_json_object(prepared),
        )
    )

    assert pdf_bytes == b"%PDF-seating"
    seating_poster_renderer.render.assert_called_once()
    request = seating_poster_renderer.render.call_args.kwargs["request"]
    assert request.roster_name == "Klass 7A"
    assert request.template_name == "Sal A"
    assert request.paper_size is SeatingExportPaperSize.A3_LANDSCAPE
    assert request.scene == prepared.poster_scene
    seating_pdf_renderer.render.assert_called_once_with(bundle=poster_bundle)
    grouping_pdf_renderer.render.assert_not_called()


@pytest.mark.unit
def test_share_pdf_renderer_uses_grouping_pdf_renderer() -> None:
    presentation = _prepared_grouping().presentation
    seating_poster_renderer = MagicMock(spec=SeatingPosterRendererProtocol)
    seating_pdf_renderer = MagicMock(spec=SeatingPdfRendererProtocol)
    grouping_pdf_renderer = MagicMock(spec=GroupingPdfRendererProtocol)
    grouping_pdf_renderer.render.return_value = b"%PDF-grouping"

    pdf_bytes = _renderer(
        seating_poster_renderer=seating_poster_renderer,
        seating_pdf_renderer=seating_pdf_renderer,
        grouping_pdf_renderer=grouping_pdf_renderer,
    ).render(
        artifact=_artifact(
            draft_kind=PlanDraftKind.GROUPING,
            presentation_payload=_json_object(presentation),
        )
    )

    assert pdf_bytes == b"%PDF-grouping"
    grouping_pdf_renderer.render.assert_called_once()
    view_model = grouping_pdf_renderer.render.call_args.kwargs["view_model"]
    assert view_model.title == "Gruppindelning"
    assert view_model.class_name == "Klass 7A"
    assert view_model.generated_label == "Skapad 2026-05-01 00:00"
    assert view_model.output_filename == "klass-7a-gruppindelning-a4-portrait.pdf"
    seating_poster_renderer.render.assert_not_called()
    seating_pdf_renderer.render.assert_not_called()


@pytest.mark.unit
def test_share_pdf_renderer_caches_rendered_pdf_for_same_immutable_artifact() -> None:
    prepared = _prepared_seating()
    poster_bundle = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content="<html>poster</html>",
        css_filename="poster.css",
        css_content="body { color: black; }",
        output_filename="klass-7a-a3.pdf",
    )
    seating_poster_renderer = MagicMock(spec=SeatingPosterRendererProtocol)
    seating_poster_renderer.render.return_value = poster_bundle
    seating_pdf_renderer = MagicMock(spec=SeatingPdfRendererProtocol)
    seating_pdf_renderer.render.return_value = b"%PDF-cached"
    artifact = _artifact(
        draft_kind=PlanDraftKind.SEATING,
        presentation_payload=_json_object(prepared),
    )
    renderer = _renderer(
        seating_poster_renderer=seating_poster_renderer,
        seating_pdf_renderer=seating_pdf_renderer,
        grouping_pdf_renderer=MagicMock(spec=GroupingPdfRendererProtocol),
    )

    assert renderer.render(artifact=artifact) == b"%PDF-cached"
    assert renderer.render(artifact=artifact) == b"%PDF-cached"

    seating_poster_renderer.render.assert_called_once()
    seating_pdf_renderer.render.assert_called_once_with(bundle=poster_bundle)


@pytest.mark.unit
def test_share_pdf_renderer_rejects_artifact_without_presentation_payload() -> None:
    renderer = _renderer(
        seating_poster_renderer=MagicMock(spec=SeatingPosterRendererProtocol),
        seating_pdf_renderer=MagicMock(spec=SeatingPdfRendererProtocol),
        grouping_pdf_renderer=MagicMock(spec=GroupingPdfRendererProtocol),
    )

    with pytest.raises(ValueError, match="missing presentation payload"):
        renderer.render(
            artifact=_artifact(
                draft_kind=PlanDraftKind.GROUPING,
                presentation_payload=None,
            )
        )


def _renderer(
    *,
    seating_poster_renderer: SeatingPosterRendererProtocol,
    seating_pdf_renderer: SeatingPdfRendererProtocol,
    grouping_pdf_renderer: GroupingPdfRendererProtocol,
) -> ExportBackedClassroomPlannerSharePdfRenderer:
    return ExportBackedClassroomPlannerSharePdfRenderer(
        seating_poster_renderer=seating_poster_renderer,
        seating_pdf_renderer=seating_pdf_renderer,
        grouping_pdf_renderer=grouping_pdf_renderer,
    )


def _prepared_seating() -> PreparedSeatingExportContract:
    return PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="Klass 7A",
        template_id=uuid4(),
        template_name="Sal A",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[],
            fixtures=[],
        ),
    )


def _prepared_grouping() -> PreparedGroupingExportContract:
    return PreparedGroupingExportContract(
        grouping_draft_id=uuid4(),
        roster_id=uuid4(),
        export_kind=GroupingExportKind.PDF,
        paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        presentation=GroupingExportPresentation(
            draft_id=uuid4(),
            class_name="Klass 7A",
            title="Gruppindelning",
            filename_stem="klass-7a-gruppindelning",
            groups=(
                GroupingPresentationGroup(
                    group_label="Grupp 1",
                    group_order=0,
                    members=(
                        GroupingPresentationMember(
                            member_order=1,
                            display_name="Ada Alm",
                        ),
                    ),
                ),
            ),
        ),
    )


def _artifact(
    *,
    draft_kind: PlanDraftKind,
    presentation_payload: JsonObject | None,
) -> ClassroomPlannerShareArtifact:
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash="sha256:stored-only",
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=draft_kind,
        title="Klass 7A",
        slug="klass-7a",
        renderer_version=_renderer_version(draft_kind),
        presentation_schema_version=f"{draft_kind.value}-share-v1",
        presentation_hash="sha256:presentation",
        content_hash="sha256:content",
        presentation_payload=presentation_payload,
        rendered_html="<html><body>Share</body></html>",
        rendered_css="body { color: black; }",
        created_at=now,
        updated_at=now,
    )


def _renderer_version(draft_kind: PlanDraftKind) -> str:
    if draft_kind is PlanDraftKind.SEATING:
        return "klassrumskartan-seating-share-renderer-v2"
    return "klassrumskartan-share-renderer-v1"


def _json_object(model: BaseModel) -> JsonObject:
    payload = model.model_dump(mode="json")
    assert isinstance(payload, dict)
    return payload
