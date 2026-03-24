"""Unit tests for the classroom-planner poster HTML/CSS renderer."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneRoom,
    PosterSceneSeat,
    SeatingExportPaperSize,
    SeatingPosterRenderRequest,
    SeatingPosterScene,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
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
                        kind=PosterSceneFixtureKind.WHITEBOARD,
                        x=0,
                        y=0,
                        width=4,
                        height=1,
                        label="Whiteboard",
                    )
                ],
            ),
        )
    )

    assert bundle.html_filename == "index.html"
    assert 'href="poster.css"' in bundle.html_content
    assert "Alice A." in bundle.html_content
    assert "Whiteboard" in bundle.html_content
    assert "@page" in bundle.css_content
    assert "A3 landscape" in bundle.css_content


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
