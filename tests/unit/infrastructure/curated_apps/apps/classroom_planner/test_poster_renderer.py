"""Unit tests for the classroom-planner poster HTML/CSS renderer."""

from __future__ import annotations

import re

import pytest

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneLabelOrientation,
    PosterSceneRoom,
    PosterSceneSeat,
    PosterSceneWallSide,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    SeatingPosterScene,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    SEATING_POSTER_LOGO_PNG_PATH,
    SEATING_POSTER_LOGO_SVG_PATH,
    BrutalistPosterRenderer,
)


@pytest.mark.unit
def test_renderer_outputs_html_linked_to_poster_css_and_seat_labels():
    renderer = BrutalistPosterRenderer()

    bundle = renderer.render(
        request=SeatingPosterRenderRequest(
            roster_name="Klass 7A",
            template_name="Sal A",
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=14, grid_rows=9),
                seats=[PosterSceneSeat(seat_id="seat-1", x=1, y=2, label="Alice A.")],
                fixtures=[
                    PosterSceneFixture(
                        fixture_id="fixture-1",
                        source_fixture_ids=("fixture-1",),
                        kind=PosterSceneFixtureKind.WHITEBOARD,
                        x=0,
                        y=0,
                        width=4,
                        height=1,
                        placement=PosterSceneFixturePlacement.WALL,
                        label="Whiteboard",
                        label_orientation=PosterSceneLabelOrientation.HORIZONTAL,
                    ),
                    PosterSceneFixture(
                        fixture_id="fixture-2",
                        source_fixture_ids=("fixture-2",),
                        kind=PosterSceneFixtureKind.DOOR,
                        x=0,
                        y=3,
                        width=1,
                        height=1,
                        placement=PosterSceneFixturePlacement.WALL,
                        wall_side=PosterSceneWallSide.LEFT,
                        label="Dörr",
                        label_orientation=PosterSceneLabelOrientation.VERTICAL,
                    ),
                ],
            ),
        )
    )

    assert bundle.html_filename == "index.html"
    assert 'href="poster.css"' in bundle.html_content
    assert "Alice A." in bundle.html_content
    assert "Whiteboard" in bundle.html_content
    assert "Dörr" in bundle.html_content
    assert "poster__floor" in bundle.html_content
    assert "poster-fixture--label-vertical" in bundle.html_content
    assert "poster__header-brand" in bundle.html_content
    expected_logo_filename = (
        SEATING_POSTER_LOGO_PNG_PATH.name
        if SEATING_POSTER_LOGO_PNG_PATH.exists()
        else SEATING_POSTER_LOGO_SVG_PATH.name
    )
    assert f'<img src="{expected_logo_filename}" alt="">' in bundle.html_content
    assert [resource.filename for resource in bundle.resource_files] == [expected_logo_filename]
    assert "@page" in bundle.css_content
    assert "A3 landscape" in bundle.css_content
    assert "margin: 10.0mm;" in bundle.css_content
    assert "@bottom-right" in bundle.css_content
    assert "position: running(pdf-brand-footer);" in bundle.css_content
    assert "rotate(-90deg)" in bundle.css_content
    assert "writing-mode: vertical-rl" not in bundle.css_content
    assert "--side-wall-band-mm:12.0" in bundle.html_content
    assert "--top-bottom-wall-band-mm:10.0" in bundle.html_content
    assert "--page-width-mm:420.0" in bundle.html_content
    assert "justify-content: center;" in bundle.css_content
    assert "font-family: var(--heading-serif);" in bundle.css_content
    assert "background: var(--brand-terracotta);" in bundle.css_content
    assert 'class="pdf-brand-footer"' in bundle.html_content
    assert 'href="https://skriptoteket.hule.education"' in bundle.html_content
    assert "poster__watermark" not in bundle.html_content
    assert ".poster__watermark" not in bundle.css_content


@pytest.mark.unit
def test_renderer_switches_page_contract_for_a4_landscape():
    renderer = BrutalistPosterRenderer()

    bundle = renderer.render(
        request=SeatingPosterRenderRequest(
            roster_name="Klass 7A",
            template_name="Sal A",
            paper_size=SeatingExportPaperSize.A4_LANDSCAPE,
            scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=10, grid_rows=8),
                seats=[],
                fixtures=[],
            ),
        )
    )

    assert "A4 landscape" in bundle.css_content
    assert bundle.output_filename.endswith("a4_landscape.pdf")


@pytest.mark.unit
def test_renderer_fits_large_classrooms_into_one_landscape_page_box():
    renderer = BrutalistPosterRenderer()

    bundle = renderer.render(
        request=SeatingPosterRenderRequest(
            roster_name="Klass 9B",
            template_name="Stor sal",
            paper_size=SeatingExportPaperSize.A4_LANDSCAPE,
            scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=22, grid_rows=14),
                seats=[],
                fixtures=[],
            ),
        )
    )

    width_match = re.search(r"--scene-width-mm:([0-9.]+);", bundle.html_content)
    height_match = re.search(r"--scene-height-mm:([0-9.]+);", bundle.html_content)
    assert width_match is not None
    assert height_match is not None
    assert float(width_match.group(1)) <= 281.0
    assert float(height_match.group(1)) <= 179.0
    assert "repeat(var(--grid-rows), 1fr)" in bundle.css_content
    assert "minmax(24mm, 1fr)" not in bundle.css_content
    assert "--side-wall-band-mm:6.0" in bundle.html_content
    assert "--page-width-mm:297.0" in bundle.html_content
