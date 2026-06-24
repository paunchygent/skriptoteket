"""Local HTML/CSS-to-PDF renderer for classroom-planner seating exports.

Purpose:
    Convert the standalone seating poster HTML/CSS bundle into a final PDF
    artifact locally with WeasyPrint so the seating export lane no longer needs
    an external conversion service for its own renderer-owned document.

Relationships:
    - Implements `SeatingPdfRendererProtocol`.
    - Consumes `RenderedSeatingPosterBundle` from the poster HTML/CSS renderer.
    - Used by seating export-job handlers in the application layer.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from skriptoteket.application.curated_apps.classroom_planner.exports.rendering import (
    RenderedSeatingPosterBundle,
)
from skriptoteket.infrastructure.documents.pdf_rendering import render_html_to_pdf_bytes
from skriptoteket.protocols.classroom_planner_exports import SeatingPdfRendererProtocol


class WeasyPrintSeatingPdfRenderer(SeatingPdfRendererProtocol):
    """Render one seating poster bundle into final PDF bytes locally."""

    def render(self, *, bundle: RenderedSeatingPosterBundle) -> bytes:
        with TemporaryDirectory(prefix="skriptoteket-seating-pdf-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            _write_bundle_files(temp_dir=temp_dir, bundle=bundle)
            return render_html_to_pdf_bytes(html=bundle.html_content, base_url=temp_dir)


def _write_bundle_files(*, temp_dir: Path, bundle: RenderedSeatingPosterBundle) -> None:
    """Materialize CSS and bundled resources under one temporary asset directory."""

    (temp_dir / bundle.css_filename).write_text(bundle.css_content, encoding="utf-8")
    for resource in bundle.resource_files:
        resource_path = temp_dir / resource.filename
        resource_path.parent.mkdir(parents=True, exist_ok=True)
        resource_path.write_bytes(resource.content_bytes)
