"""Cut a text PDF's picture regions out of its rendered pages (TASK-SKRIPT-39-10-02).

A placed picture or a drawn figure reaches the exam as the Word import's picture: a PNG
``DocxImage`` in a chunk of its own at its place in the reading order. The pixels are
the page as PDFium prints it, cut to the region, so a picture's crop and a figure's
lines and labels look exactly as on paper. Only the pages that hold a region render,
once each. A region that cannot be rendered becomes a named ``DocxMissingImage``, which
the native build turns into a teacher-review reason, never a silently dropped picture.

Relationships:
    ``exam_workspace_pdf_layout`` finds the ``PdfPictureRegion`` items;
    ``exam_workspace_pdf_chunker`` calls ``with_pictures`` between the layout and
    ``exam_workspace_pdf_blocks``, which turns each ``PdfPicture`` into a chunk.
    Rendering goes through the process-wide PDFium gate in ``pdfium_access``.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxImage, DocxMissingImage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_layout import (  # noqa: E501
    PdfItem,
    PdfLine,
    PdfPictureRegion,
    PdfTable,
)
from skriptoteket.infrastructure.documents.pdfium_access import rasterize_pdf_pages

# Pixels per PDF point for a cut picture: 180 dpi keeps a figure's thin lines and small
# labels sharp without making a full-page figure a large asset.
RENDER_SCALE = 2.5
_KIND_NAMES = {"picture": "bild", "figure": "figur"}


@dataclass(frozen=True)
class PdfPicture:
    """One cut picture region at its place in the reading order."""

    page: int
    column: int
    top: float
    picture: DocxImage | DocxMissingImage


PdfBlockItem = PdfLine | PdfTable | PdfPicture


def with_pictures(content: bytes, items: Sequence[PdfItem]) -> list[PdfBlockItem]:
    """``items`` with every picture region replaced by its cut picture, in place."""
    regions = [item for item in items if isinstance(item, PdfPictureRegion)]
    pages = sorted({region.page for region in regions})
    rendered: dict[int, Image.Image] = {}
    if pages:
        try:
            images = rasterize_pdf_pages(content, scale=RENDER_SCALE, pages=pages)
        except RuntimeError:
            images = ()
        rendered = dict(zip(pages, images, strict=False))
    return [
        _cut(item, rendered.get(item.page)) if isinstance(item, PdfPictureRegion) else item
        for item in items
    ]


def _cut(region: PdfPictureRegion, page: Image.Image | None) -> PdfPicture:
    ox, oy = region.origin
    box = (
        round((region.x0 - ox) * RENDER_SCALE),
        round((region.top - oy) * RENDER_SCALE),
        round((region.x1 - ox) * RENDER_SCALE),
        round((region.bottom - oy) * RENDER_SCALE),
    )
    picture: DocxImage | DocxMissingImage
    if page is None:
        picture = _missing(region)
    else:
        clamped = (
            max(0, box[0]),
            max(0, box[1]),
            min(page.width, box[2]),
            min(page.height, box[3]),
        )
        if clamped[0] >= clamped[2] or clamped[1] >= clamped[3]:
            picture = _missing(region)
        else:
            output = io.BytesIO()
            cut = page.crop(clamped).convert("RGB")
            cut.save(output, format="PNG")
            picture = DocxImage(
                payload=output.getvalue(),
                media_type="image/png",
                width=cut.width,
                height=cut.height,
            )
    return PdfPicture(page=region.page, column=region.column, top=region.top, picture=picture)


def _missing(region: PdfPictureRegion) -> DocxMissingImage:
    return DocxMissingImage(
        reference=f"PDF-sida {region.page + 1}: {_KIND_NAMES[region.kind]}",
        media_type="image/png",
    )
