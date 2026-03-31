"""Unit tests for the classroom-planner grouping PDF renderer.

Purpose:
    Guard the local A4 portrait handout so grouping PDF export keeps its
    branded two-column card layout and deterministic teacher-facing ordering.

Relationships:
    - Exercises `GroupingPdfRenderer`.
    - Builds the handout through the grouping PDF view model.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pypdf import PdfReader

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportPresentation,
    GroupingPdfCardPair,
    GroupingPresentationGroup,
    GroupingPresentationMember,
    build_grouping_pdf_view_model,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.grouping_pdf_renderer import (
    _GROUPING_PDF_LOGO_PNG_PATH,
    _GROUPING_PDF_LOGO_SVG_PATH,
    GroupingPdfRenderer,
    _build_html,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.pdf_branding import (
    PDF_BRANDING_ASSETS_DIR,
    resolve_local_horizontal_logo_filename,
)


def _presentation() -> GroupingExportPresentation:
    return GroupingExportPresentation(
        draft_id=uuid4(),
        class_name="SA24D",
        title="Gruppindelning",
        filename_stem="sa24d-gruppindelning",
        groups=(
            GroupingPresentationGroup(
                group_label="Grupp 1",
                group_order=0,
                members=(
                    GroupingPresentationMember(member_order=1, display_name="Ada Lovelace"),
                    GroupingPresentationMember(member_order=2, display_name="Bo Berg"),
                ),
            ),
            GroupingPresentationGroup(
                group_label="Grupp 2",
                group_order=1,
                members=(GroupingPresentationMember(member_order=1, display_name="Grace Hopper"),),
            ),
            GroupingPresentationGroup(
                group_label="Grupp 3",
                group_order=2,
                members=(
                    GroupingPresentationMember(member_order=1, display_name="Linus Torvalds"),
                ),
            ),
        ),
    )


@pytest.mark.unit
def test_build_grouping_pdf_view_model_pairs_groups_left_to_right():
    view_model = build_grouping_pdf_view_model(
        presentation=_presentation(),
        generated_at=datetime(2026, 3, 26, 12, 34, tzinfo=timezone.utc),
    )

    assert view_model.output_filename == "sa24d-gruppindelning-a4-portrait.pdf"
    assert view_model.generated_label == "Skapad 2026-03-26 12:34"
    assert len(view_model.card_pairs) == 2
    assert isinstance(view_model.card_pairs[0], GroupingPdfCardPair)
    assert isinstance(view_model.card_pairs[1], GroupingPdfCardPair)
    assert view_model.card_pairs[0].left_card.group_label == "Grupp 1"
    assert view_model.card_pairs[0].right_card is not None
    assert view_model.card_pairs[0].right_card.group_label == "Grupp 2"
    assert view_model.card_pairs[1].left_card.group_label == "Grupp 3"


@pytest.mark.unit
def test_grouping_pdf_renderer_outputs_a4_pdf_with_expected_teacher_facing_text():
    view_model = build_grouping_pdf_view_model(
        presentation=_presentation(),
        generated_at=datetime(2026, 3, 26, 12, 34, tzinfo=timezone.utc),
    )

    pdf_bytes = GroupingPdfRenderer().render(view_model=view_model)

    assert pdf_bytes.startswith(b"%PDF-")

    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) == 1

    first_page = reader.pages[0]
    assert 590 <= float(first_page.mediabox.width) <= 600
    assert 840 <= float(first_page.mediabox.height) <= 845

    text = first_page.extract_text()
    assert text is not None
    assert "Gruppindelning" in text
    assert "SA24D" in text
    assert "Skapad 2026-03-26 12:34" in text
    assert "skriptoteket.hule.education" in text
    assert "Grupp 1" in text
    assert "Grupp 2" in text
    assert "Grupp 3" in text
    assert "Ada Lovelace" in text
    assert "Grace Hopper" in text
    assert "Linus Torvalds" in text
    assert text.index("Grupp 1") < text.index("Grupp 2") < text.index("Grupp 3")


@pytest.mark.unit
def test_grouping_pdf_renderer_html_references_bundled_logo_asset():
    view_model = build_grouping_pdf_view_model(
        presentation=_presentation(),
        generated_at=datetime(2026, 3, 26, 12, 34, tzinfo=timezone.utc),
    )

    html = _build_html(
        view_model=view_model,
        logo_filename=resolve_local_horizontal_logo_filename(),
    )

    assert _GROUPING_PDF_LOGO_SVG_PATH.exists() or _GROUPING_PDF_LOGO_PNG_PATH.exists()
    expected_logo_filename = (
        _GROUPING_PDF_LOGO_SVG_PATH.name
        if _GROUPING_PDF_LOGO_SVG_PATH.exists()
        else _GROUPING_PDF_LOGO_PNG_PATH.name
    )
    assert f'<img src="{expected_logo_filename}" alt="" />' in html
    assert 'class="pdf-brand-footer"' in html
    assert 'href="https://skriptoteket.hule.education"' in html


@pytest.mark.unit
def test_grouping_pdf_renderer_passes_filesystem_base_url_to_weasyprint(monkeypatch):
    captured: dict[str, object] = {}

    class FakeHtml:
        def __init__(self, *, string: str, base_url: str) -> None:
            captured["string"] = string
            captured["base_url"] = base_url

        def write_pdf(self) -> bytes:
            return b"%PDF-fake"

    monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=FakeHtml))

    view_model = build_grouping_pdf_view_model(
        presentation=_presentation(),
        generated_at=datetime(2026, 3, 26, 12, 34, tzinfo=timezone.utc),
    )

    pdf_bytes = GroupingPdfRenderer().render(view_model=view_model)

    assert pdf_bytes == b"%PDF-fake"
    assert captured["base_url"] == str(PDF_BRANDING_ASSETS_DIR)
