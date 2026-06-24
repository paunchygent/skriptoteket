"""Reusable document processing protocols.

Purpose:
    Define small document rendering and extraction seams that curated apps can
    share for local HTML/PDF/Markdown work without depending on concrete
    third-party libraries.

Relationships:
    Implemented by ``infrastructure.documents`` adapters and injected into
    curated-app application services through Dishka providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PdfTextExtractionProbe:
    """Describe local PDF text extraction and heavy-path routing signals."""

    text: str | None
    heavy_reason: str | None = None


class HtmlToPdfRendererProtocol(Protocol):
    """Render trusted server-owned HTML into PDF bytes."""

    def render_html(self, *, html: str, base_url: str | Path | None = None) -> bytes: ...


class MarkdownToHtmlRendererProtocol(Protocol):
    """Render trusted Markdown text into HTML for local document producers."""

    def render_markdown(self, *, markdown_text: str) -> str: ...


class PdfTextExtractorProtocol(Protocol):
    """Extract simple text from PDFs before routing heavy files upstream."""

    def probe_text(self, *, file_bytes: bytes, filename: str) -> PdfTextExtractionProbe: ...

    def extract_text(self, *, file_bytes: bytes, filename: str) -> str | None: ...
