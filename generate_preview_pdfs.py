"""Generate classroom-planner PDF previews for local branding checks.

Relationships:
- Exercises the poster and seating PDF renderers with a small deterministic scene.
- Produces repo-local preview artifacts used while iterating on classroom-planner PDF branding.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.models import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneRoom,
    PosterSceneSeat,
    SeatingPosterScene,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.rendering import (
    SeatingPosterRenderRequest,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    BrutalistPosterRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_pdf_renderer import (
    WeasyPrintSeatingPdfRenderer,
)


def render_seating_preview() -> bytes:
    """Render a small deterministic seating preview PDF."""

    request = SeatingPosterRenderRequest(
        roster_name="SA24C",
        template_name="G20",
        paper_size=SeatingExportPaperSize.A4_LANDSCAPE,
        scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=18, grid_rows=12),
            seats=[
                PosterSceneSeat(seat_id="s1", x=2, y=5, label="Selma L."),
                PosterSceneSeat(seat_id="s2", x=3, y=5, label="Per S."),
                PosterSceneSeat(seat_id="s3", x=4, y=5, label="Maja B."),
                PosterSceneSeat(seat_id="s4", x=2, y=8, label="Felix L."),
                PosterSceneSeat(seat_id="s5", x=3, y=8, label="Johan H."),
                PosterSceneSeat(seat_id="s6", x=4, y=8, label="Linda P."),
            ],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="desk",
                    kind=PosterSceneFixtureKind.TEACHER_DESK,
                    placement=PosterSceneFixturePlacement.FLOOR,
                    x=2,
                    y=1,
                    width=3,
                    height=2,
                    label="KATEDER",
                )
            ],
        ),
    )
    bundle = BrutalistPosterRenderer().render(request=request)
    return WeasyPrintSeatingPdfRenderer().render(bundle=bundle)


def main() -> int:
    """Write the current seating preview PDF to disk."""

    with open("sittplatser-preview.pdf", "wb") as output_file:
        output_file.write(render_seating_preview())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
