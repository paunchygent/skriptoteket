"""Python-Markdown-backed Markdown rendering.

Purpose:
    Convert trusted Markdown input into HTML for local document producers that
    compose PDFs or other presentation artifacts inside Skriptoteket.

Relationships:
    Implements ``MarkdownToHtmlRendererProtocol`` and is consumed by the local
    Document Converter producer.
"""

from __future__ import annotations

from skriptoteket.protocols.documents import MarkdownToHtmlRendererProtocol

_DEFAULT_MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]


class PythonMarkdownToHtmlRenderer(MarkdownToHtmlRendererProtocol):
    """Render Markdown text to HTML with the repo runtime Markdown package."""

    def render_markdown(self, *, markdown_text: str) -> str:
        """Render Markdown text to HTML.

        Args:
            markdown_text: Markdown source text decoded from a validated input.

        Returns:
            HTML suitable for server-side PDF composition.
        """
        import markdown as markdown_lib

        return markdown_lib.markdown(
            markdown_text,
            extensions=_DEFAULT_MARKDOWN_EXTENSIONS,
            output_format="html",
        )
