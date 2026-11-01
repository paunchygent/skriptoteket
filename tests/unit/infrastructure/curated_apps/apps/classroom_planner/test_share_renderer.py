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
    PosterSceneRoom,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    CLASSROOM_PLANNER_PUBLIC_APP_PATH,
    SHARE_CREATED_DATE_CHROME_SLOT,
    SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
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

    assert rendered.renderer_version == "klassrumskartan-share-renderer-v2"
    assert rendered.presentation_schema_version == "grouping-share-v1"
    assert rendered.presentation_payload["class_name"] == 'Klass <7A> & "X"'
    assert (
        rendered.rendered_html.count('data-skriptoteket-share-pdf-download-controller="owned"') == 1
    )
    assert "<script>alert" not in rendered.rendered_html.casefold()
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
    assert "room-seat" not in rendered.rendered_css
    assert "room-frame" not in rendered.rendered_css
    assert "Klass &lt;7A&gt; &amp; &quot;X&quot;" in rendered.rendered_html
    assert "Ada &amp; &lt;script&gt;alert(2)&lt;/script&gt;" in rendered.rendered_html
    assert '<meta name="robots" content="noindex,nofollow">' in rendered.rendered_html
    assert '<meta property="og:title"' in rendered.rendered_html
    assert "Ada &" not in rendered.rendered_css
    assert f"Skapad: {SHARE_CREATED_DATE_CHROME_SLOT}" in rendered.rendered_html
    assert SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT in rendered.rendered_html
    assert "Ladda ner PDF" in rendered.rendered_html
    assert f'href="{CLASSROOM_PLANNER_PUBLIC_APP_PATH}"' in rendered.rendered_html
    assert "https://skriptoteket.hule.education/public/apps" not in rendered.rendered_html
    assert "Skapad av Klassrumskartan" in rendered.rendered_html
    assert ".share-origin-link {\n  border-bottom: 1px solid currentColor;" in (
        rendered.rendered_css
    )


@pytest.mark.unit
def test_share_page_titles_use_en_dash_between_class_and_kind() -> None:
    renderer = StaticClassroomPlannerShareRenderer()

    grouping = renderer.render_grouping(
        prepared_export=PreparedGroupingExportContract(
            grouping_draft_id=uuid4(),
            roster_id=uuid4(),
            export_kind=GroupingExportKind.PDF,
            paper_size=GroupingExportPaperSize.A4_PORTRAIT,
            presentation=GroupingExportPresentation(
                draft_id=uuid4(),
                class_name="Klass 7A",
                title="Gruppindelning",
                filename_stem="klass-7a",
                groups=(),
            ),
        ),
    )
    seating = renderer.render_seating(
        prepared_export=PreparedSeatingExportContract(
            seating_draft_id=uuid4(),
            roster_id=uuid4(),
            roster_name="Klass 8B",
            template_id=uuid4(),
            template_name="Sal 214",
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            poster_scene=SeatingPosterScene(
                room=PosterSceneRoom(grid_cols=4, grid_rows=3),
                seats=[],
                fixtures=[],
            ),
        ),
    )

    assert grouping.title == "Klass 7A – Gruppindelning"
    assert seating.title == "Klass 8B – Sittschema"
    for rendered, title in (
        (grouping, "Klass 7A – Gruppindelning"),
        (seating, "Klass 8B – Sittschema"),
    ):
        assert " - " not in rendered.title
        assert f"<title>{title}</title>" in rendered.rendered_html
        assert f'<h1 class="share-title">{title}</h1>' in rendered.rendered_html
