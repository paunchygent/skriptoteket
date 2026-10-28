"""Text PDFs for the PDF import reader's tests, typeset by WeasyPrint from small HTML pages."""

from __future__ import annotations

import base64
import io

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject
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


def picture_only_pdf() -> bytes:
    """One A4 PDF whose page holds a placed PNG and no glyph at all."""
    picture = io.BytesIO()
    Image.new("RGB", (120, 80), (40, 90, 160)).save(picture, format="PNG")
    uri = base64.b64encode(picture.getvalue()).decode("ascii")
    return pdf_bytes(
        f'<p><img src="data:image/png;base64,{uri}" style="width:120pt;height:80pt"></p>'
    )


def garbled(content: bytes) -> bytes:
    """``content`` with every font's character map and embedded font program removed.

    A reader then knows a glyph sits on the page but not which character it is, so
    pdfplumber yields pdfminer's ``(cid:NN)`` placeholders instead of the words.
    """
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(content)))
    for page in writer.pages:
        resources = _resolved(page.get("/Resources"))
        if not isinstance(resources, DictionaryObject):
            continue
        fonts = _resolved(resources.get("/Font"))
        if not isinstance(fonts, DictionaryObject):
            continue
        for reference in fonts.values():
            font = _resolved(reference)
            if not isinstance(font, DictionaryObject):
                continue
            font.pop("/ToUnicode", None)
            descendants = _resolved(font.get("/DescendantFonts", []))
            if not isinstance(descendants, ArrayObject):
                continue
            for descendant in descendants:
                holder = _resolved(descendant)
                if not isinstance(holder, DictionaryObject):
                    continue
                descriptor = _resolved(holder.get("/FontDescriptor"))
                if not isinstance(descriptor, DictionaryObject):
                    continue
                for name in ("/FontFile", "/FontFile2", "/FontFile3"):
                    descriptor.pop(name, None)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def merged(*contents: bytes) -> bytes:
    """The PDFs' pages concatenated in order, each source keeping its own fonts."""
    writer = PdfWriter()
    for content in contents:
        writer.append(PdfReader(io.BytesIO(content)))
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _resolved(value: object) -> object:
    """The object behind a pypdf indirect reference, or ``value`` itself."""
    return value.get_object() if isinstance(value, IndirectObject) else value
