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

from dataclasses import dataclass
from html import escape

from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.models import (
    PosterSceneFixture,
    PosterSceneFixturePlacement,
    PosterSceneLabelOrientation,
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
        grid_cols = request.scene.room.grid_cols
        grid_rows = request.scene.room.grid_rows
        layout = _build_poster_page_layout(
            paper_size=request.paper_size,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
        )
        html = f"""<!doctype html>
<html lang="sv">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="poster.css">
  </head>
  <body
    class="paper-{paper_token}"
    style="--page-width-mm:{layout.page_width_mm};--page-height-mm:{layout.page_height_mm};"
  >
    <main
      class="poster"
      style="
        --poster-content-width-mm:{layout.content_width_mm};
        --poster-content-height-mm:{layout.content_height_mm};
        --poster-header-height-mm:{layout.header_height_mm};
        --poster-gap-mm:{layout.header_gap_mm};
        --scene-width-mm:{layout.scene_width_mm};
        --scene-height-mm:{layout.scene_height_mm};
        --wall-band-track:{layout.wall_band_ratio}fr;
        --scene-gap-mm:{layout.scene_gap_mm};
        --scene-border-mm:{layout.scene_border_mm};
        --floor-border-mm:{layout.floor_border_mm};
        --seat-font:{layout.seat_font_pt}pt;
        --fixture-font:{layout.fixture_font_pt}pt;
      "
    >
      <header class="poster__header">
        <p class="poster__eyebrow">Klassrumskartan</p>
        <h1>{escape(request.roster_name)}</h1>
        <p class="poster__meta">{escape(request.template_name)}</p>
      </header>
      <section
        class="poster__scene"
        style="--grid-cols:{grid_cols};--grid-rows:{grid_rows};"
      >
        <div class="poster__floor"></div>
        {self._render_floor_fixtures(request.scene.fixtures, grid_cols, grid_rows)}
        {self._render_seats(request.scene.seats)}
        {self._render_wall_fixtures(request.scene.fixtures, grid_cols, grid_rows)}
      </section>
    </main>
  </body>
</html>
"""
        return RenderedSeatingPosterBundle(
            html_filename="index.html",
            html_content=html,
            css_filename="poster.css",
            css_content=_build_css(request.paper_size, layout=layout),
            output_filename=f"{_slugify(request.roster_name)}-{request.paper_size.value}.pdf",
        )

    def _render_seats(self, seats: list[PosterSceneSeat]) -> str:
        rendered: list[str] = []
        for seat in seats:
            label = escape(seat.label or "Tom plats")
            rendered.append(
                (
                    '<article class="poster-seat" '
                    f'style="grid-column:{seat.x + 2};grid-row:{seat.y + 2};">'
                    f'<span class="poster-seat__label">{label}</span>'
                    "</article>"
                )
            )
        return "\n        ".join(rendered)

    def _render_floor_fixtures(
        self,
        fixtures: list[PosterSceneFixture],
        grid_cols: int,
        grid_rows: int,
    ) -> str:
        floor_fixtures = [
            fixture
            for fixture in fixtures
            if fixture.placement is PosterSceneFixturePlacement.FLOOR
        ]
        return self._render_fixtures(
            fixtures=floor_fixtures,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
        )

    def _render_wall_fixtures(
        self,
        fixtures: list[PosterSceneFixture],
        grid_cols: int,
        grid_rows: int,
    ) -> str:
        wall_fixtures = [
            fixture for fixture in fixtures if fixture.placement is PosterSceneFixturePlacement.WALL
        ]
        return self._render_fixtures(
            fixtures=wall_fixtures,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
        )

    def _render_fixtures(
        self,
        fixtures: list[PosterSceneFixture],
        grid_cols: int,
        grid_rows: int,
    ) -> str:
        rendered: list[str] = []
        for fixture in fixtures:
            label = escape(fixture.label) if fixture.label else ""
            label_classes = ["poster-fixture__label"]
            fixture_style = self._build_fixture_grid_style(
                fixture,
                grid_cols=grid_cols,
                grid_rows=grid_rows,
            )
            classes = ["poster-fixture", f"poster-fixture--{fixture.kind.value}"]
            classes.append(f"poster-fixture--{fixture.tone.value}")
            if fixture.variant is not None:
                classes.append(f"poster-fixture--{fixture.variant.value}")
            if fixture.wall_side is not None:
                classes.append(f"poster-fixture--wall-{fixture.wall_side.value}")
            if fixture.label_orientation is PosterSceneLabelOrientation.VERTICAL:
                classes.append("poster-fixture--label-vertical")
            label_markup = (
                f'<span class="{" ".join(label_classes)}">{label}</span>' if label else ""
            )
            rendered.append(
                (
                    f'<article class="{" ".join(classes)}" '
                    f'style="{fixture_style}">'
                    f"{label_markup}"
                    "</article>"
                )
            )
        return "\n        ".join(rendered)

    def _build_fixture_grid_style(
        self,
        fixture: PosterSceneFixture,
        *,
        grid_cols: int,
        grid_rows: int,
    ) -> str:
        if fixture.placement is PosterSceneFixturePlacement.FLOOR:
            return (
                f"grid-column:{fixture.x + 2}/span {fixture.width};"
                f"grid-row:{fixture.y + 2}/span {fixture.height};"
            )

        if fixture.wall_side is None:
            return (
                f"grid-column:{fixture.x + 2}/span {fixture.width};"
                f"grid-row:{fixture.y + 2}/span {fixture.height};"
            )

        if fixture.wall_side.value == "top":
            return f"grid-column:{fixture.x + 2}/span {fixture.width};grid-row:1;"
        if fixture.wall_side.value == "bottom":
            return f"grid-column:{fixture.x + 2}/span {fixture.width};grid-row:{grid_rows + 2};"
        if fixture.wall_side.value == "left":
            return f"grid-column:1;grid-row:{fixture.y + 2}/span {fixture.height};"
        return f"grid-column:{grid_cols + 2};grid-row:{fixture.y + 2}/span {fixture.height};"


def _slugify(value: str) -> str:
    """Return a conservative output slug for generated filenames."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"


@dataclass(frozen=True, slots=True)
class _PosterPageLayout:
    """Describe the fitted page box and scene box for one rendered poster."""

    page_width_mm: float
    page_height_mm: float
    page_margin_mm: float
    content_width_mm: float
    content_height_mm: float
    header_height_mm: float
    header_gap_mm: float
    scene_width_mm: float
    scene_height_mm: float
    wall_band_ratio: float
    scene_gap_mm: float
    scene_border_mm: float
    floor_border_mm: float
    seat_font_pt: float
    fixture_font_pt: float


def _build_poster_page_layout(
    *,
    paper_size: SeatingExportPaperSize,
    grid_cols: int,
    grid_rows: int,
) -> _PosterPageLayout:
    """Fit the classroom scene into one landscape page with tighter chrome."""

    if paper_size is SeatingExportPaperSize.A3_LANDSCAPE:
        page_width_mm = 420.0
        page_height_mm = 297.0
        page_margin_mm = 10.0
        header_height_mm = 24.0
        header_gap_mm = 5.0
    else:
        page_width_mm = 297.0
        page_height_mm = 210.0
        page_margin_mm = 8.0
        header_height_mm = 19.0
        header_gap_mm = 4.0

    content_width_mm = page_width_mm - (page_margin_mm * 2)
    content_height_mm = page_height_mm - (page_margin_mm * 2)
    max_scene_width_mm = content_width_mm
    max_scene_height_mm = content_height_mm - header_height_mm - header_gap_mm
    wall_band_ratio = 0.32
    scene_units_width = grid_cols + (wall_band_ratio * 2)
    scene_units_height = grid_rows + (wall_band_ratio * 2)

    width_limited_height = max_scene_width_mm * (scene_units_height / scene_units_width)
    if width_limited_height <= max_scene_height_mm:
        scene_width_mm = max_scene_width_mm
        scene_height_mm = width_limited_height
    else:
        scene_height_mm = max_scene_height_mm
        scene_width_mm = max_scene_height_mm * (scene_units_width / scene_units_height)

    cell_mm = min(
        scene_width_mm / scene_units_width,
        scene_height_mm / scene_units_height,
    )
    seat_font_pt = min(18.0, max(8.5, cell_mm * 0.8))
    fixture_font_pt = min(10.5, max(6.2, cell_mm * 0.45))

    return _PosterPageLayout(
        page_width_mm=_round_layout_value(page_width_mm),
        page_height_mm=_round_layout_value(page_height_mm),
        page_margin_mm=_round_layout_value(page_margin_mm),
        content_width_mm=_round_layout_value(content_width_mm),
        content_height_mm=_round_layout_value(content_height_mm),
        header_height_mm=_round_layout_value(header_height_mm),
        header_gap_mm=_round_layout_value(header_gap_mm),
        scene_width_mm=_round_layout_value(scene_width_mm),
        scene_height_mm=_round_layout_value(scene_height_mm),
        wall_band_ratio=wall_band_ratio,
        scene_gap_mm=0.8,
        scene_border_mm=1.2,
        floor_border_mm=1.0,
        seat_font_pt=_round_layout_value(seat_font_pt),
        fixture_font_pt=_round_layout_value(fixture_font_pt),
    )


def _round_layout_value(value: float) -> float:
    """Round one layout scalar to two decimals for stable HTML/CSS output."""

    return round(value, 2)


def _build_css(
    paper_size: SeatingExportPaperSize,
    *,
    layout: _PosterPageLayout,
) -> str:
    """Build the dedicated poster stylesheet for one paper contract."""

    page_size = (
        "A3 landscape" if paper_size is SeatingExportPaperSize.A3_LANDSCAPE else "A4 landscape"
    )
    return f"""@page {{
  size: {page_size};
  margin: 0;
}}
:root {{
  --ink: #111111;
  --paper: #ffffff;
  --accent: #111111;
  --grid-line: #11111122;
}}
* {{
  box-sizing: border-box;
}}
html,
body {{
  margin: 0;
  padding: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: \"Helvetica Neue\", Arial, sans-serif;
  width: calc(var(--page-width-mm) * 1mm);
  height: calc(var(--page-height-mm) * 1mm);
}}
body {{
  display: flex;
  align-items: center;
  justify-content: center;
}}
.poster {{
  display: grid;
  width: calc(var(--poster-content-width-mm) * 1mm);
  height: calc(var(--poster-content-height-mm) * 1mm);
  grid-template-rows: calc(var(--poster-header-height-mm) * 1mm) 1fr;
  gap: calc(var(--poster-gap-mm) * 1mm);
  overflow: hidden;
}}
.poster__header {{
  display: grid;
  gap: 1.2mm;
  align-content: start;
  overflow: hidden;
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
  font-size: 22pt;
  line-height: 0.96;
  overflow-wrap: anywhere;
}}
.poster__meta {{
  font-size: 10pt;
}}
.poster__scene {{
  display: grid;
  width: calc(var(--scene-width-mm) * 1mm);
  height: calc(var(--scene-height-mm) * 1mm);
  justify-self: center;
  align-self: center;
  grid-template-columns:
    var(--wall-band-track)
    repeat(var(--grid-cols), 1fr)
    var(--wall-band-track);
  grid-template-rows:
    var(--wall-band-track)
    repeat(var(--grid-rows), 1fr)
    var(--wall-band-track);
  gap: calc(var(--scene-gap-mm) * 1mm);
  border: calc(var(--scene-border-mm) * 1mm) solid var(--ink);
  background: #ffffff;
  overflow: hidden;
}}
.poster__floor {{
  grid-column: 2 / span var(--grid-cols);
  grid-row: 2 / span var(--grid-rows);
  border: calc(var(--floor-border-mm) * 1mm) solid var(--ink);
  background-color: #ffffff;
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
  padding: 0.8mm;
  border: calc(var(--floor-border-mm) * 1mm) solid var(--ink);
  text-align: center;
  overflow: hidden;
}}
.poster-seat {{
  background: #ffffff;
}}
.poster-seat__label {{
  font-size: var(--seat-font);
  font-weight: 700;
  line-height: 1.05;
}}
.poster-fixture {{
  background: #ffffff;
  font-size: var(--fixture-font);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  line-height: 1;
}}
.poster-fixture__label {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-inline-size: 100%;
  text-align: center;
}}
.poster-fixture--outline,
.poster-fixture--whiteboard,
.poster-fixture--window,
.poster-fixture--door,
.poster-fixture--table {{
  background: #ffffff;
}}
.poster-fixture--muted {{
  background: #d7d7d7;
}}
.poster-fixture--strong {{
  background: #222222;
  color: #ffffff;
}}
.poster-fixture--door,
.poster-fixture--window {{
  border-style: solid;
}}
.poster-fixture--wall-top,
.poster-fixture--wall-bottom {{
  margin-block: 0.6mm;
}}
.poster-fixture--wall-left,
.poster-fixture--wall-right {{
  margin-inline: 0.5mm;
}}
.poster-fixture--whiteboard.poster-fixture--wall-top,
.poster-fixture--whiteboard.poster-fixture--wall-bottom {{
  margin-block: 1.8mm;
}}
.poster-fixture--whiteboard.poster-fixture--wall-left,
.poster-fixture--whiteboard.poster-fixture--wall-right {{
  margin-inline: 1.2mm;
}}
.poster-fixture--teacher_desk {{
  border-width: calc(var(--scene-border-mm) * 1mm);
}}
.poster-fixture--round {{
  border-radius: 999px;
}}
.poster-fixture--label-vertical {{
  position: relative;
  padding: 0;
}}
.poster-fixture--label-vertical .poster-fixture__label {{
  position: absolute;
  top: 50%;
  left: 50%;
  white-space: nowrap;
  max-inline-size: none;
  letter-spacing: 0.04em;
  transform: translate(-50%, -50%) rotate(-90deg);
  transform-origin: center;
}}
"""
