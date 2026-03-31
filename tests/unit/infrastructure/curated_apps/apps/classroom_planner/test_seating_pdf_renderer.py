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
    PosterSceneRoom,
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
