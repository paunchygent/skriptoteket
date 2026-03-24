"""Unit tests for seating export-job support helpers."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    seating_export_job_support,
)


@pytest.mark.unit
def test_build_job_spec_uses_author_owned_page_css_mode_for_renderer_owned_page_contract():
    spec = seating_export_job_support.build_job_spec(
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        source_filename="poster.html",
        css_filename="poster.css",
    )

    source = spec.get("source")
    assert isinstance(source, dict)
    assert source == {
        "kind": "upload",
        "filename": "poster.html",
        "format": "html",
    }

    conversion = spec.get("conversion")
    assert isinstance(conversion, dict)
    assert conversion["page_css_mode"] == "author_owned"
    assert "pdf_layout" not in conversion
