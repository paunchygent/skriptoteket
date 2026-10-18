"""WeasyPrint print-PDF renderer for the printed exam house template (TASK-SKRIPT-40-04-07 W1).

Purpose:
    Materialize the house-template print HTML (student or facit) as PDF bytes, and
    rasterize the same document into preview page PNGs with the page each question
    first appears on. The preview serves the Förhandsgranska panel (W5); the PDF
    serves the printed export (W1). It renders the print HTML and nothing else: the
    Exam.net import PDF keeps its own renderer.

Relationships:
    Implements ``ExamPrintRendererProtocol``. Calls WeasyPrint directly for the PDF
    (pictures are data URIs, so no base URL is needed) and pypdfium2 for the page
    images, mirroring the labeler's rasterizing pattern. It is a pure leaf: it
    renders and returns bytes and writes nothing back.
"""

from __future__ import annotations

import asyncio

from skriptoteket.protocols.exam_workspace import (
    ExamPrintPreviewPages,
    ExamPrintRendererProtocol,
)

PREVIEW_SCALE = 1.5  # about 108 dpi: sharp enough on screen, small enough to send
_ITEM_ANCHOR_PREFIX = "exam-item-"


class WeasyPrintExamPrintRenderer(ExamPrintRendererProtocol):
    """Render the house-template print HTML to PDF bytes and preview page PNGs."""

    def render_pdf(self, *, html: str) -> bytes:
        """Render the print HTML into PDF bytes."""
        from weasyprint import HTML

        return HTML(string=html).write_pdf()

    async def render_preview(self, *, html: str) -> ExamPrintPreviewPages:
        """Render the print HTML into one PNG per page plus each question's first page."""
        return await asyncio.to_thread(self._preview, html)

    def _preview(self, html: str) -> ExamPrintPreviewPages:
        from weasyprint import HTML

        document = HTML(string=html).render()
        question_pages: dict[str, int] = {}
        for index, page in enumerate(document.pages):
            for name in page.anchors:
                if not name.startswith(_ITEM_ANCHOR_PREFIX):
                    continue
                item_id = name[len(_ITEM_ANCHOR_PREFIX) :]
                question_pages.setdefault(item_id, index)
        return ExamPrintPreviewPages(
            pages=self._page_pngs(document.write_pdf()),
            question_pages=question_pages,
        )

    def _page_pngs(self, pdf: bytes) -> tuple[bytes, ...]:
        import io

        import pypdfium2

        document = pypdfium2.PdfDocument(pdf)
        try:
            pages: list[bytes] = []
            for index in range(len(document)):
                image = document[index].render(scale=PREVIEW_SCALE).to_pil()
                output = io.BytesIO()
                image.save(output, format="PNG")
                pages.append(output.getvalue())
        finally:
            document.close()
        return tuple(pages)
