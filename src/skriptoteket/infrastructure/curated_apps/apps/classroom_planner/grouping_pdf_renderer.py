"""Local HTML/CSS-to-PDF renderer for classroom-planner grouping exports.

Purpose:
    Render the shared grouping presentation as a restrained A4 portrait handout
    with a branded letterhead and two-column framed group cards, then convert
    that export-owned HTML/CSS to PDF locally with WeasyPrint.

Relationships:
    - Implements `GroupingPdfRendererProtocol`.
    - Consumes the application-layer grouping PDF view model.
"""

from __future__ import annotations

from html import escape

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    grouping_pdf_view_model,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.pdf_branding import (
    HORIZONTAL_LOGO_PNG_PATH,
    HORIZONTAL_LOGO_SVG_PATH,
    build_pdf_brand_footer_css,
    build_pdf_brand_footer_margin_box_css,
    render_pdf_brand_footer_markup,
    resolve_local_horizontal_logo_base_dir,
    resolve_local_horizontal_logo_filename,
)
from skriptoteket.protocols.classroom_planner_exports import GroupingPdfRendererProtocol

_GROUPING_PDF_LOGO_PNG_PATH = HORIZONTAL_LOGO_PNG_PATH
_GROUPING_PDF_LOGO_SVG_PATH = HORIZONTAL_LOGO_SVG_PATH


class GroupingPdfRenderer(GroupingPdfRendererProtocol):
    """Render the grouping PDF handout bytes for one grouping draft."""

    def __init__(self) -> None:
        self._logo_filename = resolve_local_horizontal_logo_filename()
        self._asset_base_dir = resolve_local_horizontal_logo_base_dir()

    def render(
        self,
        *,
        view_model: grouping_pdf_view_model.GroupingPdfViewModel,
    ) -> bytes:
        from weasyprint import HTML

        html = _build_html(view_model=view_model, logo_filename=self._logo_filename)
        rendered_pdf = HTML(string=html, base_url=str(self._asset_base_dir)).write_pdf()
        if not isinstance(rendered_pdf, bytes):
            raise TypeError("Grouping PDF renderer must return bytes.")
        return rendered_pdf


def _build_html(
    *,
    view_model: grouping_pdf_view_model.GroupingPdfViewModel,
    logo_filename: str | None,
) -> str:
    """Build the export-owned HTML document for the grouping PDF handout."""

    return f"""<!doctype html>
<html lang="sv">
  <head>
    <meta charset="utf-8">
    <title>{escape(view_model.output_filename)}</title>
    <style>
      {_build_css()}
    </style>
  </head>
  <body>
    {render_pdf_brand_footer_markup()}
    <main class="page">
      <header class="letterhead">
        <div class="letterhead__copy">
          <h1>{escape(view_model.title)}</h1>
          <p class="letterhead__meta">{escape(view_model.class_name)}</p>
          <p class="letterhead__stamp">{escape(view_model.generated_label)}</p>
        </div>
        {_render_logo(logo_filename=logo_filename)}
      </header>
      <section class="group-grid">
        {_render_card_pairs(card_pairs=view_model.card_pairs)}
      </section>
    </main>
  </body>
</html>"""


def _render_logo(*, logo_filename: str | None) -> str:
    """Render the restrained letterhead logo markup when the asset is available."""

    if logo_filename is None:
        return ""
    return (
        '<div class="letterhead__brand" aria-hidden="true">'
        f'<img src="{escape(logo_filename)}" alt="" />'
        "</div>"
    )


def _render_card_pairs(
    *,
    card_pairs: tuple[grouping_pdf_view_model.GroupingPdfCardPair, ...],
) -> str:
    """Render deterministic left-right group card rows."""

    rendered_pairs: list[str] = []
    for pair in card_pairs:
        right_card_markup = (
            _render_card(card=pair.right_card)
            if pair.right_card is not None
            else '<div class="group-card group-card--placeholder" aria-hidden="true"></div>'
        )
        rendered_pairs.append(
            '<section class="group-row">'
            f"{_render_card(card=pair.left_card)}"
            f"{right_card_markup}"
            "</section>"
        )
    return "".join(rendered_pairs)


def _render_card(*, card: grouping_pdf_view_model.GroupingPdfCard) -> str:
    """Render one framed group card."""

    member_rows = "".join(
        "<tr>"
        f'<td class="group-card__number">{member.member_order}</td>'
        f"<td>{escape(member.display_name)}</td>"
        "</tr>"
        for member in card.members
    )
    return (
        '<article class="group-card">'
        f"<h2>{escape(card.group_label)}</h2>"
        '<table class="group-card__table">'
        "<thead><tr><th>Nr</th><th>Elev</th></tr></thead>"
        f"<tbody>{member_rows}</tbody>"
        "</table>"
        "</article>"
    )


def _build_css() -> str:
    """Build the dedicated A4 portrait handout stylesheet."""

    return (
        """
      @page {
        size: A4 portrait;
        margin: 14mm 12mm 16mm 12mm;
"""
        + build_pdf_brand_footer_margin_box_css()
        + """
      }

      :root {
        --heading-serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino,
          Georgia, serif;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        color: #0f172a;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 9.8pt;
        line-height: 1.35;
        background: #ffffff;
      }

      .page {
        width: 100%;
      }

      .letterhead {
        position: relative;
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10mm;
        padding-bottom: 5.5mm;
        margin-bottom: 7mm;
      }

      .letterhead::after {
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 1.2pt;
        background: #1c2e4a;
      }

      .letterhead::before {
        content: "";
        position: absolute;
        right: 0;
        bottom: 0;
        width: 16mm;
        height: 2.2pt;
        background: #4d1521;
      }

      .letterhead h1 {
        margin: 0 0 1.8mm;
        color: #1c2e4a;
        font-family: var(--heading-serif);
        font-size: 20pt;
        font-weight: 700;
        letter-spacing: -0.01em;
        line-height: 1.1;
      }

      .letterhead__meta,
      .letterhead__stamp {
        margin: 0;
      }

      .letterhead__copy {
        flex: 1 1 0;
        min-width: 0;
      }

      .letterhead__meta {
        font-size: 10.2pt;
        font-weight: 700;
      }

      .letterhead__stamp {
        margin-top: 1.2mm;
        color: #475569;
        font-size: 8.5pt;
      }

      .letterhead__brand {
        flex: 0 0 42mm;
        display: flex;
        align-items: flex-start;
        justify-content: flex-end;
        margin-left: auto;
        margin-top: 1mm;
        width: 42mm;
        height: 9.25mm;
      }

      .letterhead__brand img {
        display: block;
        width: 100%;
        max-width: 42mm;
        max-height: 9.25mm;
        object-fit: contain;
        object-position: center right;
      }

      .group-grid {
        width: 100%;
      }

      .group-row {
        display: flex;
        align-items: flex-start;
        gap: 5.5mm;
        margin-bottom: 5.5mm;
      }

      .group-card {
        flex: 1 1 0;
        width: calc((100% - 5.5mm) / 2);
        min-width: 0;
        break-inside: avoid;
        page-break-inside: avoid;
        border: 1pt solid #bcc8da;
        border-top: 2.2pt solid #1c2e4a;
        border-radius: 1.6mm;
        padding: 4.2mm 4mm 3.5mm;
        background: #ffffff;
      }

      .group-card--placeholder {
        visibility: hidden;
        border: 0;
        padding: 0;
      }

      .group-card h2 {
        margin: -4.2mm -4mm 3mm;
        padding: 2.8mm 4mm 2.6mm;
        border-bottom: 0.8pt solid #d9e0ea;
        background: #f7f9fc;
        color: #1c2e4a;
        font-family: var(--heading-serif);
        font-size: 12.1pt;
        font-weight: 700;
        letter-spacing: 0.01em;
        line-height: 1.15;
      }

      .group-card__table {
        width: 100%;
        border-collapse: collapse;
      }

      .group-card__table thead th {
        padding: 0 0 1.8mm;
        border-bottom: 0.8pt solid #cbd5e1;
        color: #475569;
        font-size: 8.2pt;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-align: left;
        text-transform: uppercase;
      }

      .group-card__table tbody td {
        padding: 1.4mm 0;
        border-bottom: 0.4pt solid #e2e8f0;
        vertical-align: top;
      }

      .group-card__table tbody tr:last-child td {
        border-bottom: 0;
      }

      .group-card__number {
        width: 10mm;
        padding-right: 3mm;
        font-weight: 700;
        white-space: nowrap;
      }
"""
        + build_pdf_brand_footer_css()
    )
