from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    reader = PdfReader(BytesIO(pdf_bytes))
    text_chunks: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted:
            text_chunks.append(extracted)
    return "\n".join(text_chunks)
