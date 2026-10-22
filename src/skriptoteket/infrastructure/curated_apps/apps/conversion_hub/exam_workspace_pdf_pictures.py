"""Cut a text PDF's picture regions out of its rendered pages (TASK-SKRIPT-39-10-02).

A placed picture or a drawn figure reaches the exam as the Word import's picture: a PNG
``DocxImage`` in a chunk of its own at its place in the reading order. The pixels are
the page as PDFium prints it, cut to the region, so a picture's crop and a figure's
lines and labels look exactly as on paper. Words that stay text are painted white
wherever they fall inside a cut, so answer text never reaches a picture's pixels;
a cut's own label words are kept. Only the pages that hold a region render,
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

from PIL import Image, ImageDraw

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxImage, DocxMissingImage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfItem,
    PdfLine,
    PdfPictureRegion,
    PdfTable,
)
from skriptoteket.infrastructure.documents.pdfium_access import rasterize_pdf_pages

# Pixels per PDF point for a cut picture: 180 dpi keeps a figure's thin lines and small
# labels sharp without making a full-page figure a large asset.
RENDER_SCALE = 2.5
# Each erased word box grows this many points on every side before painting white,
# covering anti-aliased glyph edges that spill past the word box.
_ERASE_GROW_POINTS = 0.5
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
    picture: DocxImage | DocxMissingImage
    if page is None or not region.mapped:
        picture = _missing(region)
    else:
        vx0, vy0, vx1, vy1 = region.visible
        expected = (round((vx1 - vx0) * RENDER_SCALE), round((vy1 - vy0) * RENDER_SCALE))
        box = (
            round((region.x0 - vx0) * RENDER_SCALE),
            round((region.top - vy0) * RENDER_SCALE),
            round((region.x1 - vx0) * RENDER_SCALE),
            round((region.bottom - vy0) * RENDER_SCALE),
        )
        if (
            abs(page.width - expected[0]) > 2
            or abs(page.height - expected[1]) > 2
            or box[0] >= box[2]
            or box[1] >= box[3]
        ):
            picture = _missing(region)
        else:
            output = io.BytesIO()
            cut = page.crop(box).convert("RGB")
            _whiteout(cut, region)
            cut.save(output, format="PNG")
            picture = DocxImage(
                payload=output.getvalue(),
                media_type="image/png",
                width=cut.width,
                height=cut.height,
            )
    return PdfPicture(page=region.page, column=region.column, top=region.top, picture=picture)


def _whiteout(cut: Image.Image, region: PdfPictureRegion) -> None:
    """Paint white over every non-label word falling inside the cut.

    Each erase box maps with the same ``visible`` origin and ``RENDER_SCALE`` as the
    crop, relative to the crop's top-left, grown by half a point for anti-aliasing.
    A cut's own label words are kept: they are not in ``erase``.
    """
    if not region.erase:
        return
    paint = ImageDraw.Draw(cut)
    for x0, top, x1, bottom in region.erase:
        left = max(0, round((x0 - _ERASE_GROW_POINTS - region.x0) * RENDER_SCALE))
        upper = max(0, round((top - _ERASE_GROW_POINTS - region.top) * RENDER_SCALE))
        right = min(cut.width, round((x1 + _ERASE_GROW_POINTS - region.x0) * RENDER_SCALE))
        lower = min(cut.height, round((bottom + _ERASE_GROW_POINTS - region.top) * RENDER_SCALE))
        if left < right and upper < lower:
            paint.rectangle([left, upper, right, lower], fill="white")


def _missing(region: PdfPictureRegion) -> DocxMissingImage:
    return DocxMissingImage(
        reference=f"PDF-sida {region.page + 1}: {_KIND_NAMES[region.kind]}",
        media_type="image/png",
    )
