"""Text PDFs for the PDF import reader's tests, typeset by WeasyPrint from small HTML pages."""

from __future__ import annotations

from weasyprint import HTML

_BASE_CSS = """
@page { size: A4; margin: 2.5cm; }
body { font-family: 'DejaVu Sans'; font-size: 11pt; }
p { margin: 0 0 8pt 0; }
h1 { font-size: 20pt; }
h2 { font-size: 14pt; }
"""


def pdf_bytes(body: str, *, css: str = "") -> bytes:
    """One A4 PDF with a text layer: ``body`` in DejaVu Sans 11pt, ``css`` after the base."""
    html = f"<html><head><style>{_BASE_CSS}{css}</style></head><body>{body}</body></html>"
    content = HTML(string=html).write_pdf()
    assert content is not None
    return content
