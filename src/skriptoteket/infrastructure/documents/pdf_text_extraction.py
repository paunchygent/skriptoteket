"""pdfplumber-backed simple PDF text extraction.

Purpose:
    Detect and extract text from simple text PDFs locally so Document Converter
    can route only OCR/no-text or complex PDF paths to the producer boundary.

Relationships:
    Implements ``PdfTextExtractorProtocol`` for Document Converter routing and
    can be reused by other curated apps that need local PDF text probing.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from typing import Any

from skriptoteket.protocols.documents import PdfTextExtractionProbe, PdfTextExtractorProtocol

logger = logging.getLogger(__name__)

_FORMULA_SYMBOLS = frozenset(
    "\u2211\u222b\u221a\u2248\u2260\u2264\u2265\u00b1\u00d7\u00f7"
    "\u221e\u03c0\u03bb\u03bc\u03c3\u03b1\u03b2\u03b3\u03b8"
)
_FORMULA_ASSIGNMENT_PATTERN = re.compile(r"\b[A-Za-z]\s*(?:=|<=|>=|~=)\s*[-+*/^()0-9A-Za-z]")
_LATEX_FORMULA_PATTERN = re.compile(r"\\(?:frac|sum|int|sqrt)|[_^][{A-Za-z0-9]")
_FORMULA_HEAVY_SCORE = 3
_MAX_SIMPLE_GRAPHIC_OBJECTS = 8
_MAX_SIMPLE_GRAPHIC_OBJECTS_PER_PAGE = 6


@dataclass(frozen=True)
class _PdfProbeStats:
    page_texts: list[str]
    table_count: int
    graphic_object_count: int
    image_count: int


class PdfPlumberTextExtractor(PdfTextExtractorProtocol):
    """Extract simple text from PDF bytes using pdfplumber."""

    def probe_text(self, *, file_bytes: bytes, filename: str) -> PdfTextExtractionProbe:
        """Return text plus heavy-path signals for one PDF upload.

        Args:
            file_bytes: Validated PDF upload bytes.
            filename: Input filename for diagnostics.

        Returns:
            Extracted text and, when detected, a Sir Convert routing reason for
            formula-heavy, table-dense, or layout-complex documents.
        """
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                stats = _collect_probe_stats(pdf.pages)
        except Exception as exc:
            logger.info(
                "Local PDF text extraction failed; routing to producer",
                extra={
                    "filename": filename,
                    "error_type": type(exc).__name__,
                },
            )
            return PdfTextExtractionProbe(text=None)

        text = "\n".join(stats.page_texts).strip()
        if not any(character.isalpha() for character in text):
            return PdfTextExtractionProbe(text=None)

        return PdfTextExtractionProbe(
            text=text,
            heavy_reason=_classify_heavy_pdf(text=text, stats=stats),
        )

    def extract_text(self, *, file_bytes: bytes, filename: str) -> str | None:
        """Return extracted PDF text, or ``None`` when local extraction is unsuitable.

        Args:
            file_bytes: Validated PDF upload bytes.
            filename: Input filename for diagnostics.

        Returns:
            Extracted text when at least one alphabetic character is found;
            otherwise ``None`` so callers can route heavy paths explicitly.
        """
        probe = self.probe_text(file_bytes=file_bytes, filename=filename)
        if probe.heavy_reason is not None:
            return None
        return probe.text


def _collect_probe_stats(pages: list[Any]) -> _PdfProbeStats:
    page_texts: list[str] = []
    table_count = 0
    graphic_object_count = 0
    image_count = 0
    for page in pages:
        page_texts.append(page.extract_text() or "")
        table_count += len(page.find_tables())
        image_count += len(page.images)
        graphic_object_count += len(page.lines) + len(page.rects) + len(page.curves)
    return _PdfProbeStats(
        page_texts=page_texts,
        table_count=table_count,
        graphic_object_count=graphic_object_count,
        image_count=image_count,
    )


def _classify_heavy_pdf(*, text: str, stats: _PdfProbeStats) -> str | None:
    if stats.table_count > 0:
        return "table_dense_pdf"
    if _formula_score(text) >= _FORMULA_HEAVY_SCORE:
        return "formula_heavy_pdf"
    page_count = max(len(stats.page_texts), 1)
    graphic_limit = max(
        _MAX_SIMPLE_GRAPHIC_OBJECTS,
        page_count * _MAX_SIMPLE_GRAPHIC_OBJECTS_PER_PAGE,
    )
    if stats.image_count > 0 or stats.graphic_object_count > graphic_limit:
        return "layout_complex_pdf"
    return None


def _formula_score(text: str) -> int:
    symbol_score = sum(1 for character in text if character in _FORMULA_SYMBOLS)
    assignment_score = len(_FORMULA_ASSIGNMENT_PATTERN.findall(text)) * 2
    latex_score = len(_LATEX_FORMULA_PATTERN.findall(text)) * 3
    return symbol_score + assignment_score + latex_score
