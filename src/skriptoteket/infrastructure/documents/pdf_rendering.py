"""WeasyPrint-backed HTML-to-PDF rendering.

Purpose:
    Provide the shared local HTML/CSS-to-PDF adapter for curated apps that own
    their document rendering inside the Skriptoteket app boundary.

Relationships:
    Implements ``HtmlToPdfRendererProtocol`` and replaces duplicated direct
    WeasyPrint calls in app-local PDF renderers.
"""

from __future__ import annotations

from pathlib import Path

from skriptoteket.protocols.documents import HtmlToPdfRendererProtocol


class WeasyPrintHtmlToPdfRenderer(HtmlToPdfRendererProtocol):
    """Render server-owned HTML to PDF bytes with WeasyPrint."""

    def render_html(self, *, html: str, base_url: str | Path | None = None) -> bytes:
        """Render one HTML document into PDF bytes.

        Args:
            html: Complete or fragment HTML owned by server-side code.
            base_url: Optional filesystem or URL base for relative assets.

        Returns:
            The rendered PDF payload.

        Raises:
            TypeError: If WeasyPrint returns a non-byte payload.
        """
        return render_html_to_pdf_bytes(html=html, base_url=base_url)


def render_html_to_pdf_bytes(*, html: str, base_url: str | Path | None = None) -> bytes:
    """Render HTML to PDF bytes using the shared WeasyPrint call pattern."""
    from weasyprint import HTML

    html_kwargs: dict[str, object] = {"string": html}
    if base_url is not None:
        html_kwargs["base_url"] = str(base_url)
    rendered_pdf = HTML(**html_kwargs).write_pdf()
    if isinstance(rendered_pdf, bytes):
        return rendered_pdf
    if isinstance(rendered_pdf, bytearray):
        return bytes(rendered_pdf)
    raise TypeError("WeasyPrint returned a non-bytes PDF payload.")
