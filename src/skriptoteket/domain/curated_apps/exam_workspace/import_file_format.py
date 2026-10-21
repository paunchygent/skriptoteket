"""Tell a Word-lane import's file format from its bytes (ST-SKRIPT-39-10 P5).

The Word import lane converts Word files (.docx) and text PDFs (.pdf) through one path and
keeps only the uploaded bytes. A PDF begins with its ``%PDF-`` header; a Word file is a ZIP
package and never does.
"""

from __future__ import annotations

_PDF_HEADER = b"%PDF-"


def is_pdf(content: bytes) -> bool:
    """True when ``content`` begins with a PDF file header."""
    return content.startswith(_PDF_HEADER)
