"""Process-wide PDFium access gate for every production rasterizer.

Purpose:
    PDFium is inherently not thread-safe. The pypdfium2 binding documentation
    states that it is "not allowed to call pdfium functions simultaneously across
    different threads, not even with different documents" and that threaded use is
    only safe when a mutex ensures a single pdfium call at a time
    (https://pypdfium2.readthedocs.io/en/stable/python_api.html, "Incompatibility
    with Threading"). Request-scoped renderer instances give no cross-request
    boundary, so this module owns the one process-wide lock that every production
    caller rasterizes through.

Relationships:
    ``WeasyPrintExamPrintRenderer._page_pngs`` (print preview) and
    ``DocxBlockImageRenderer.render`` (labeler block images) both call
    ``rasterize_pdf_pages``. It is the only Skriptoteket module that imports
    pypdfium2; nothing pypdfium2-typed escapes the lock, and callers encode or
    crop the returned PIL images outside it.
"""

from __future__ import annotations

import threading

import pypdfium2
from PIL import Image

_PDFIUM_LOCK = threading.Lock()


def rasterize_pdf_pages(pdf: bytes, *, scale: float) -> tuple[Image.Image, ...]:
    """Render every page of ``pdf`` to an independent PIL image at ``scale``.

    The whole open/render/close sequence holds the process-wide PDFium lock.
    Each bitmap is copied into a fresh PIL image so the result owns its pixels and
    stays valid after the PDFium document is closed and the lock is released.
    Callers do all further work (encoding, cropping, conversion) outside the lock.

    Args:
        pdf: Complete PDF bytes to rasterize.
        scale: Pixels per PDF point; 1.0 renders at 72 dpi.

    Returns:
        One independent PIL image per page, in page order.
    """
    with _PDFIUM_LOCK:
        document = pypdfium2.PdfDocument(pdf)
        try:
            return tuple(
                document[index].render(scale=scale).to_pil().copy()
                for index in range(len(document))
            )
        finally:
            document.close()
