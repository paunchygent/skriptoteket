"""Unit tests for the static Klassrumskartan share renderer.

Purpose:
    Prove share pages are rendered server-side from canonical presentation
    contracts with stable provenance and hostile classroom text escaped in body,
    title, preview metadata, and CSS-adjacent contexts.

Relationships:
    - Exercises `StaticClassroomPlannerShareRenderer`.
    - Covers the ADR-0084 renderer provenance guardrail for PR-0274.
"""

from __future__ import annotations

import re
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    GroupingExportPresentation,
    GroupingPresentationGroup,
    GroupingPresentationMember,
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneFixtureTone,
    PosterSceneRoom,
    PosterSceneSeat,
    PosterSceneWallSide,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    StaticClassroomPlannerShareRenderer,
)


@pytest.mark.unit
def test_grouping_renderer_escapes_hostile_values_and_records_provenance() -> None:
    prepared = PreparedGroupingExportContract(
        grouping_draft_id=uuid4(),
        roster_id=uuid4(),
        export_kind=GroupingExportKind.PDF,
        paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        presentation=GroupingExportPresentation(
            draft_id=uuid4(),
            class_name='Klass <7A> & "X"',
            title='Gruppindelning </title><script>alert("x")</script>',
            filename_stem="klass-7a",
            groups=(
                GroupingPresentationGroup(
                    group_label="Grupp </style><script>alert(1)</script>",
                    group_order=0,
                    members=(
                        GroupingPresentationMember(
                            member_order=1,
                            display_name="Ada & <script>alert(2)</script>",
                        ),
                    ),
                ),
                GroupingPresentationGroup(
                    group_label="Grupp 2",
                    group_order=1,
                    members=(
                        GroupingPresentationMember(
                            member_order=1,
                            display_name="Bea Berg",
                        ),
                        GroupingPresentationMember(
                            member_order=2,
                            display_name="Cia Ceder",
                        ),
                    ),
                ),
            ),
        ),
    )

    rendered = StaticClassroomPlannerShareRenderer().render_grouping(prepared_export=prepared)

    assert rendered.renderer_version == "klassrumskartan-share-renderer-v1"
    assert rendered.presentation_schema_version == "grouping-share-v1"
    assert rendered.presentation_payload["class_name"] == 'Klass <7A> & "X"'
    assert "<script" not in rendered.rendered_html.casefold()
    assert "</style><script>" not in rendered.rendered_html
    assert "<script" not in rendered.rendered_css.casefold()
    assert 'class="share-page share-page--grouping"' in rendered.rendered_html
    assert 'class="groups-grid"' in rendered.rendered_html
    assert 'class="group-card"' in rendered.rendered_html
    assert 'class="group-count">1 elev</span>' in rendered.rendered_html
    assert 'class="group-count">2 elever</span>' in rendered.rendered_html
    assert 'class="student-number">1</span>' in rendered.rendered_html
    assert 'class="student-name">Ada &amp; &lt;script&gt;alert(2)&lt;/script&gt;</span>' in (
        rendered.rendered_html
    )
    assert "group-list" not in rendered.rendered_html
    assert "share-card" not in rendered.rendered_html
    assert "Klass &lt;7A&gt; &amp; &quot;X&quot;" in rendered.rendered_html
    assert "Ada &amp; &lt;script&gt;alert(2)&lt;/script&gt;" in rendered.rendered_html
    assert '<meta name="robots" content="noindex,nofollow">' in rendered.rendered_html
    assert '<meta property="og:title"' in rendered.rendered_html
    assert "Ada &" not in rendered.rendered_css


@pytest.mark.unit
def test_seating_renderer_escapes_hostile_values_and_records_provenance() -> None:
    prepared = PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="Klass <8B>",
        template_id=uuid4(),
        template_name='Sal </style><script>alert("room")</script>',
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[
                PosterSceneSeat(
                    seat_id="seat-1",
                    x=0,
                    y=1,
                    student_id="student-1",
                    label="Bo <img src=x onerror=alert(1)>",
                ),
                PosterSceneSeat(seat_id="seat-2", x=1, y=1),
            ],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="whiteboard-1",
                    kind=PosterSceneFixtureKind.WHITEBOARD,
                    x=2,
                    y=0,
                    width=3,
                    height=1,
                    placement=PosterSceneFixturePlacement.WALL,
                    wall_side=PosterSceneWallSide.TOP,
                    label='Whiteboard </style><script>alert("fixture")</script>',
                ),
                PosterSceneFixture(
                    fixture_id="teacher-desk-1",
                    kind=PosterSceneFixtureKind.TEACHER_DESK,
                    x=5,
                    y=0,
                    width=2,
                    height=1,
                    placement=PosterSceneFixturePlacement.FLOOR,
                    label="Kateder",
                ),
            ],
        ),
    )

    rendered = StaticClassroomPlannerShareRenderer().render_seating(prepared_export=prepared)

    assert rendered.renderer_version == "klassrumskartan-share-renderer-v1"
    assert rendered.presentation_schema_version == "seating-share-v1"
    assert rendered.presentation_payload["roster_name"] == "Klass <8B>"
    assert "<script" not in rendered.rendered_html.casefold()
    assert "<script>" not in rendered.rendered_html.casefold()
    assert "<img" not in rendered.rendered_html.casefold()
    assert "<script" not in rendered.rendered_css.casefold()
    assert "resize" not in rendered.rendered_html.casefold()
    assert 'class="share-page share-page--seating"' in rendered.rendered_html
    assert "room-surface" in rendered.rendered_html
    assert "room-floor" in rendered.rendered_html
    assert "room-fixture--whiteboard" in rendered.rendered_html
    assert "room-fixture--teacher-desk" in rendered.rendered_html
    assert "room-seat--empty" in rendered.rendered_html
    empty_seat_markup = rendered.rendered_html.split('class="room-seat room-seat--empty"', 1)[1]
    empty_seat_markup = empty_seat_markup.split("</article>", 1)[0]
    assert "room-seat__id" not in rendered.rendered_html
    assert "room-seat__name-line" not in empty_seat_markup
    assert "Bo" in rendered.rendered_html
    assert "seat-grid" not in rendered.rendered_html
    assert "Rad " not in rendered.rendered_html
    assert "Klass &lt;8B&gt;" in rendered.rendered_html
    assert "Sal &lt;/style&gt;&lt;script&gt;alert(&quot;room&quot;)&lt;/script&gt;" in (
        rendered.rendered_html
    )
    assert "Bo &lt;img src=x onerror=alert(1)&gt;" in rendered.rendered_html
    assert "Whiteboard &lt;/style&gt;&lt;script&gt;alert(&quot;fixture&quot;)&lt;/script&gt;" in (
        rendered.rendered_html
    )
    assert '<meta name="robots" content="noindex,nofollow">' in rendered.rendered_html
    assert "Bo <img" not in rendered.rendered_css


@pytest.mark.unit
def test_seating_renderer_centers_labeled_merged_bench_overlay() -> None:
    prepared = PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="Klass 9C",
        template_id=uuid4(),
        template_name="Sal G20",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[
                PosterSceneSeat(
                    seat_id="seat-1",
                    x=3,
                    y=4,
                    student_id="student-1",
                    label="Ada Alm",
                ),
            ],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="bench-left__bench-right",
                    source_fixture_ids=("bench-left", "bench-right"),
                    kind=PosterSceneFixtureKind.BENCH,
                    x=2,
                    y=3,
                    width=4,
                    height=1,
                    placement=PosterSceneFixturePlacement.FLOOR,
                    label="Bänk",
                    tone=PosterSceneFixtureTone.MUTED,
                ),
            ],
        ),
    )

    rendered = StaticClassroomPlannerShareRenderer().render_seating(prepared_export=prepared)

    assert 'class="room-fixture room-fixture--bench room-fixture--muted"' in (
        rendered.rendered_html
    )
    assert (
        '<div class="room-bench-body"></div><span class="room-fixture__label">Bänk</span>'
        in rendered.rendered_html
    )
    assert ".room-fixture--bench {\n  background: transparent;\n  display: block;" in (
        rendered.rendered_css
    )
    assert ".room-fixture--bench .room-bench-body" in rendered.rendered_css
    assert "left: 0.375rem;" in rendered.rendered_css
    assert "right: 0.375rem;" in rendered.rendered_css
    assert ".room-fixture--bench .room-fixture__label" in rendered.rendered_css
    assert "left: 50%;" in rendered.rendered_css
    assert "transform: translate(-50%, -50%);" in rendered.rendered_css


@pytest.mark.unit
def test_seating_renderer_places_top_wall_fixture_above_floor_band() -> None:
    prepared = PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="Klass 9C",
        template_id=uuid4(),
        template_name="Sal G20",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="whiteboard-top",
                    kind=PosterSceneFixtureKind.WHITEBOARD,
                    x=2,
                    y=0,
                    width=4,
                    height=1,
                    placement=PosterSceneFixturePlacement.WALL,
                    wall_side=PosterSceneWallSide.TOP,
                    label="Whiteboard",
                ),
            ],
        ),
    )

    rendered = StaticClassroomPlannerShareRenderer().render_seating(prepared_export=prepared)

    floor_style = _style_for_class(rendered.rendered_html, "room-floor")
    whiteboard_style = _style_for_class(rendered.rendered_html, "room-fixture--whiteboard")
    assert whiteboard_style["top"] < floor_style["top"]
    assert whiteboard_style["height"] < floor_style["top"]


@pytest.mark.unit
def test_seating_renderer_rejects_wall_fixture_missing_wall_side() -> None:
    prepared = PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="Klass 9C",
        template_id=uuid4(),
        template_name="Sal G20",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="whiteboard-missing-side",
                    kind=PosterSceneFixtureKind.WHITEBOARD,
                    x=2,
                    y=0,
                    width=4,
                    height=1,
                    placement=PosterSceneFixturePlacement.WALL,
                    label="Whiteboard",
                ),
            ],
        ),
    )

    with pytest.raises(ValueError, match="Wall fixture is missing wall_side"):
        StaticClassroomPlannerShareRenderer().render_seating(prepared_export=prepared)


def _style_for_class(rendered_html: str, class_name: str) -> dict[str, float]:
    match = re.search(rf'class="[^"]*{class_name}[^"]*" style="([^"]+)"', rendered_html)
    assert match is not None
    style: dict[str, float] = {}
    for declaration in match.group(1).split(";"):
        if not declaration:
            continue
        key, value = declaration.split(":", 1)
        style[key] = float(value.removesuffix("%"))
    return style
