"""Unit tests for the local classroom-planner seating PDF renderer.

Purpose:
    Guard the PR-0146 local WeasyPrint lane so seating poster HTML/CSS bundles
    become final PDFs without depending on an external converter service.

Relationships:
    - Exercises `WeasyPrintSeatingPdfRenderer`.
    - Uses the standalone poster bundle contract produced by the poster renderer.
"""

from __future__ import annotations

import sys
from io import BytesIO
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneFixtureTone,
    PosterSceneRoom,
    PosterSceneSeat,
    RenderedSeatingPosterBundle,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    SeatingPosterScene,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.rendering import (
    RenderedSeatingPosterResource,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    BrutalistPosterRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_pdf_renderer import (
    WeasyPrintSeatingPdfRenderer,
)


@pytest.mark.unit
def test_seating_pdf_renderer_outputs_pdf_with_expected_teacher_facing_text():
    bundle = BrutalistPosterRenderer().render(
        request=SeatingPosterRenderRequest(
            roster_name="Klass 7A",
            template_name="Sal A",
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=10, grid_rows=8),
                seats=[],
                fixtures=[],
            ),
        )
    )

    pdf_bytes = WeasyPrintSeatingPdfRenderer().render(bundle=bundle)

    assert pdf_bytes.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(pdf_bytes))
    text = reader.pages[0].extract_text()
    assert text is not None
    assert "Klass 7A" in text
    assert "Sal A" in text
    assert "skriptoteket.hule.education" in text


@pytest.mark.unit
def test_seating_poster_renderer_uses_share_inspired_spatial_print_markup():
    bundle = BrutalistPosterRenderer().render(
        request=SeatingPosterRenderRequest(
            roster_name="SA24D",
            template_name="G20",
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=12, grid_rows=9),
                seats=[
                    PosterSceneSeat(
                        seat_id="seat-1",
                        x=1,
                        y=2,
                        student_id="kerstin-aitman",
                        label="Kerstin A.",
                    )
                ],
                fixtures=[
                    PosterSceneFixture(
                        fixture_id="bench-1",
                        kind=PosterSceneFixtureKind.BENCH,
                        x=1,
                        y=3,
                        width=2,
                        height=1,
                        placement=PosterSceneFixturePlacement.FLOOR,
                        tone=PosterSceneFixtureTone.MUTED,
                        label="Bänk",
                    ),
                    PosterSceneFixture(
                        fixture_id="whiteboard",
                        kind=PosterSceneFixtureKind.WHITEBOARD,
                        x=1,
                        y=0,
                        width=4,
                        height=1,
                        placement=PosterSceneFixturePlacement.WALL,
                        label="Whiteboard",
                    ),
                ],
            ),
        )
    )

    assert 'class="poster-seat__token"' in bundle.html_content
    assert 'class="poster-seat__name-line">Kerstin</span>' in bundle.html_content
    assert 'class="poster-seat__name-line">A.</span>' in bundle.html_content
    assert "Whiteboard" in bundle.html_content
    assert "Bänk" not in bundle.html_content
    assert 'class="poster-seat__token" style="width:' in bundle.html_content
    assert "height:" in bundle.html_content
    assert "font-size: var(--seat-long-font);" in bundle.css_content
    assert "linear-gradient(to right" not in bundle.css_content
    assert "transform: translateY(-1.5mm);" in bundle.css_content
    assert ".poster-fixture--bench::before" in bundle.css_content
    assert ".poster-fixture--whiteboard::after" in bundle.css_content
    assert ".poster-fixture--door::after" not in bundle.css_content
    assert "background: rgba(28, 46, 74, 0.86);" not in bundle.css_content


@pytest.mark.unit
def test_seating_pdf_renderer_passes_temp_filesystem_base_url_to_weasyprint(monkeypatch):
    captured: dict[str, object] = {}

    class FakeHtml:
        def __init__(self, *, string: str, base_url: str) -> None:
            captured["string"] = string
            captured["base_url"] = base_url

        def write_pdf(self) -> bytes:
            base_dir = captured["base_url"]
            assert isinstance(base_dir, str)
            css_path = f"{base_dir}/poster.css"
            logo_path = f"{base_dir}/logo.svg"
            with open(css_path, encoding="utf-8") as handle:
                captured["css"] = handle.read()
            with open(logo_path, "rb") as handle:
                captured["logo"] = handle.read()
            return b"%PDF-fake"

    monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=FakeHtml))

    bundle = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content='<html><head><link rel="stylesheet" href="poster.css"></head>'
        '<body><img src="logo.svg" alt="" /></body></html>',
        css_filename="poster.css",
        css_content="body { color: black; }",
        resource_files=[
            RenderedSeatingPosterResource(filename="logo.svg", content_bytes=b"<svg />"),
        ],
        output_filename="klass-7a-a3.pdf",
    )

    pdf_bytes = WeasyPrintSeatingPdfRenderer().render(bundle=bundle)

    assert pdf_bytes == b"%PDF-fake"
    assert isinstance(captured["base_url"], str)
    assert captured["css"] == "body { color: black; }"
    assert captured["logo"] == b"<svg />"
