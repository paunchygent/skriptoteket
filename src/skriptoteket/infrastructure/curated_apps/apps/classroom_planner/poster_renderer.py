"""Standalone HTML/CSS renderer for classroom-planner poster exports.

Purpose:
    Render the PR-0118 `poster_scene` into export-owned HTML and CSS so
    classroom-planner export jobs can hand a renderer-independent artifact
    bundle to Sir Convert-a-Lot without reusing planner DOM or styles.

Relationships:
    - Implements `SeatingPosterRendererProtocol`.
    - Consumed by seating export-job handlers in the application layer.
"""

from __future__ import annotations

from html import escape

from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.models import (
    PosterSceneFixture,
    PosterSceneSeat,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.rendering import (
    RenderedSeatingPosterBundle,
    SeatingPosterRenderRequest,
)
from skriptoteket.protocols.classroom_planner_exports import SeatingPosterRendererProtocol


class BrutalistPosterRenderer(SeatingPosterRendererProtocol):
    """Render a seating poster as export-owned HTML plus a dedicated CSS file."""

    def render(self, *, request: SeatingPosterRenderRequest) -> RenderedSeatingPosterBundle:
        title = f"{request.roster_name} - {request.template_name}"
        paper_token = request.paper_size.value.replace("_", "-")
        html = f"""<!doctype html>
<html lang="sv">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="poster.css">
  </head>
  <body class="paper-{paper_token}">
    <main class="poster">
      <header class="poster__header">
        <p class="poster__eyebrow">Klassrumskartan</p>
        <h1>{escape(request.roster_name)}</h1>
        <p class="poster__meta">{escape(request.template_name)}</p>
      </header>
      <section
        class="poster__room"
        style="--grid-cols:{request.scene.room.grid_cols};--grid-rows:{request.scene.room.grid_rows};"
      >
        {self._render_fixtures(request.scene.fixtures)}
        {self._render_seats(request.scene.seats)}
      </section>
    </main>
  </body>
</html>
"""
        return RenderedSeatingPosterBundle(
            html_filename="index.html",
            html_content=html,
            css_filename="poster.css",
            css_content=_build_css(request.paper_size),
            output_filename=f"{_slugify(request.roster_name)}-{request.paper_size.value}.pdf",
        )

    def _render_seats(self, seats: list[PosterSceneSeat]) -> str:
        rendered: list[str] = []
        for seat in seats:
            label = escape(seat.label or "Tom plats")
            rendered.append(
                (
                    '<article class="poster-seat" '
                    f'style="grid-column:{seat.x + 1};grid-row:{seat.y + 1};">'
                    f'<span class="poster-seat__label">{label}</span>'
                    "</article>"
                )
            )
        return "\n        ".join(rendered)

    def _render_fixtures(self, fixtures: list[PosterSceneFixture]) -> str:
        rendered: list[str] = []
        for fixture in fixtures:
            label = escape(fixture.label or fixture.kind.value.replace("_", " "))
            classes = ["poster-fixture", f"poster-fixture--{fixture.kind.value}"]
            if fixture.variant is not None:
                classes.append(f"poster-fixture--{fixture.variant.value}")
            if fixture.wall_side is not None:
                classes.append(f"poster-fixture--wall-{fixture.wall_side.value}")
            rendered.append(
                (
                    f'<article class="{" ".join(classes)}" '
                    f'style="grid-column:{fixture.x + 1}/span {fixture.width};'
                    f'grid-row:{fixture.y + 1}/span {fixture.height};">'
                    f'<span class="poster-fixture__label">{label}</span>'
                    "</article>"
                )
            )
        return "\n        ".join(rendered)


def _slugify(value: str) -> str:
    """Return a conservative output slug for generated filenames."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"


def _build_css(paper_size: SeatingExportPaperSize) -> str:
    """Build the dedicated poster stylesheet for one paper contract."""

    page_size = (
        "A3 landscape" if paper_size is SeatingExportPaperSize.A3_LANDSCAPE else "A4 landscape"
    )
    seat_font_size = "18pt" if paper_size is SeatingExportPaperSize.A3_LANDSCAPE else "13pt"
    return f"""@page {{
  size: {page_size};
  margin: 12mm;
}}

:root {{
  --ink: #111111;
  --paper: #f6f1e8;
  --accent: #d84f2a;
  --grid-line: #11111122;
  --seat-font: {seat_font_size};
}}

* {{
  box-sizing: border-box;
}}

html, body {{
  margin: 0;
  padding: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: \"Helvetica Neue\", Arial, sans-serif;
}}

.poster {{
  display: grid;
  gap: 10mm;
}}

.poster__header {{
  display: grid;
  gap: 2mm;
}}

.poster__eyebrow {{
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 9pt;
}}

.poster__header h1,
.poster__meta,
.poster-fixture__label,
.poster-seat__label {{
  margin: 0;
}}

.poster__header h1 {{
  font-size: 24pt;
  line-height: 1;
}}

.poster__meta {{
  font-size: 11pt;
}}

.poster__room {{
  display: grid;
  grid-template-columns: repeat(var(--grid-cols), 1fr);
  grid-template-rows: repeat(var(--grid-rows), minmax(24mm, 1fr));
  gap: 2mm;
  padding: 4mm;
  border: 2px solid var(--ink);
  background-image:
    linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
  background-size:
    calc(100% / var(--grid-cols)) 100%,
    100% calc(100% / var(--grid-rows));
}}

.poster-seat,
.poster-fixture {{
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2mm;
  border: 2px solid var(--ink);
  text-align: center;
}}

.poster-seat {{
  background: #fff8f0;
}}

.poster-seat__label {{
  font-size: var(--seat-font);
  font-weight: 700;
  line-height: 1.05;
}}

.poster-fixture {{
  background: #efe8dc;
  font-size: 9pt;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}}

.poster-fixture--whiteboard {{
  background: #ffffff;
}}

.poster-fixture--door,
.poster-fixture--window {{
  border-style: dashed;
}}

.poster-fixture--teacher_desk {{
  background: #d84f2a;
  color: #ffffff;
}}

.poster-fixture--round {{
  border-radius: 999px;
}}
"""
