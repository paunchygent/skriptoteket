"""Tell a Word-lane import's file format from its bytes (ST-SKRIPT-39-10 P5).

The Word import lane converts Word files (.docx) and text PDFs (.pdf) through one path and
keeps only the uploaded bytes. A PDF begins with its ``%PDF-`` header; a Word file is a ZIP
package and never does.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    DocumentImportOriginKind,
)

_PDF_HEADER = b"%PDF-"


def is_pdf(content: bytes) -> bool:
    """True when ``content`` begins with a PDF file header."""
    return content.startswith(_PDF_HEADER)


def import_origin_kind(content: bytes) -> DocumentImportOriginKind:
    """The Word-lane origin the uploaded bytes carry: PDF for PDF bytes, Word otherwise."""
    return "pdf_import" if is_pdf(content) else "docx_import"
