"""The WeasyPrint print renderer returns PDF bytes and item-anchored page PNGs (W1/W5)."""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_print_renderer import (
    WeasyPrintExamPrintRenderer,
)

pytestmark = pytest.mark.unit

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_HTML = """<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><style>
@page { size: A4; margin: 20mm; }
.second-page { break-before: page; }
</style></head>
<body>
  <section id="exam-item-a"><p>Frage A</p></section>
  <section id="exam-item-b" class="second-page"><p>Frage B</p></section>
</body></html>"""


def test_render_pdf_returns_pdf_bytes() -> None:
    renderer = WeasyPrintExamPrintRenderer()

    assert renderer.render_pdf(html=_HTML).startswith(b"%PDF")


async def test_render_preview_returns_one_png_per_page_and_first_question_pages() -> None:
    renderer = WeasyPrintExamPrintRenderer()

    preview = await renderer.render_preview(html=_HTML)

    assert len(preview.pages) == 2
    assert all(page.startswith(_PNG_SIGNATURE) for page in preview.pages)
    assert preview.question_pages == {"a": 0, "b": 1}
