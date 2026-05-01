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
