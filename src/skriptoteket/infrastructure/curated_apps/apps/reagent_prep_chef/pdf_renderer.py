"""Local PDF rendering for Reagent Prep Chef exports.

Purpose:
    Convert server-owned Reagent Prep Chef preparation and risk-assessment HTML
    into PDF bytes inside Skriptoteket using the shared document rendering
    adapter.

Relationships:
    Implements ``ReagentPrepChefPdfRendererProtocol`` and delegates the
    third-party WeasyPrint call pattern to ``infrastructure.documents``.
"""

from __future__ import annotations

from skriptoteket.infrastructure.documents.pdf_rendering import render_html_to_pdf_bytes
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefPdfRendererProtocol


class WeasyPrintPdfRenderer(ReagentPrepChefPdfRendererProtocol):
    """Render Reagent Prep Chef HTML documents into PDF bytes."""

    def render_html(self, *, html: str) -> bytes:
        return render_html_to_pdf_bytes(html=html)
