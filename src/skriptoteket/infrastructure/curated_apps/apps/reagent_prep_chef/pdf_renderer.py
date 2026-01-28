from __future__ import annotations

from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefPdfRendererProtocol


class WeasyPrintPdfRenderer(ReagentPrepChefPdfRendererProtocol):
    def render_html(self, *, html: str) -> bytes:
        from weasyprint import HTML

        pdf: bytes = HTML(string=html).write_pdf()
        return pdf
