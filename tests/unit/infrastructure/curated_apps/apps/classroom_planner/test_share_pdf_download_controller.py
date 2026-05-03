"""Unit tests for shared-link PDF download busy controller markup.

Purpose:
    Prove the public share-page `Ladda ner PDF` action has one approved
    browser-handoff controller, canonical disabled/busy affordances, and no
    API-style behavior.

Relationships:
    - Exercises `StaticClassroomPlannerShareRenderer` output.
    - Complements public share route and PDF renderer tests for PR-0282.
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
    PreparedGroupingExportContract,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    StaticClassroomPlannerShareRenderer,
)


@pytest.mark.unit
def test_share_pdf_download_action_has_bounded_disabled_busy_controller() -> None:
    rendered = StaticClassroomPlannerShareRenderer().render_grouping(
        prepared_export=PreparedGroupingExportContract(
            grouping_draft_id=uuid4(),
            roster_id=uuid4(),
            export_kind=GroupingExportKind.PDF,
            paper_size=GroupingExportPaperSize.A4_PORTRAIT,
            presentation=GroupingExportPresentation(
                draft_id=uuid4(),
                class_name="Klass 7A",
                title="Gruppindelning",
                filename_stem="klass-7a-gruppindelning",
                groups=(
                    GroupingPresentationGroup(
                        group_label="Grupp 1",
                        group_order=0,
                        members=(
                            GroupingPresentationMember(
                                member_order=1,
                                display_name="Ada Alm",
                            ),
                        ),
                    ),
                ),
            ),
        )
    )

    script_tags = re.findall(r"<script\b[^>]*>", rendered.rendered_html)
    expected_html = (
        'class="share-download-pdf__label">Ladda ner PDF</span>',
        'class="share-download-pdf__spinner" aria-hidden="true"',
        'data-skriptoteket-share-pdf-download-state="idle"',
        'data-skriptoteket-share-pdf-busy-label="Förbereder PDF"',
        "setAttribute('aria-busy', 'true')",
        "setAttribute('aria-disabled', 'true')",
        "removeAttribute('aria-disabled')",
        "setAttribute('data-skriptoteket-share-pdf-download-state', 'busy')",
        "setAttribute('data-skriptoteket-share-pdf-busy-started-at', String(Date.now()))",
        "removeAttribute('data-skriptoteket-share-pdf-busy-started-at')",
        "downloadHrefs = new WeakMap()",
        "downloadHrefs.set(action, action.getAttribute('href') || '')",
        "action.removeAttribute('href')",
        "action.setAttribute('href', downloadHrefs.get(action))",
        "event.stopImmediatePropagation();",
        "window.addEventListener('pageshow', clearAllBusy);",
        "window.addEventListener('focus', clearRecoveredBusy);",
        "browserHandoffGuardMs = 1800",
        "minimumFocusRecoveryMs = 1000",
        "document.addEventListener('visibilitychange'",
    )
    expected_css = (
        ".share-download-pdf__spinner",
        '.share-download-pdf[data-skriptoteket-share-pdf-download-state="busy"]',
        "cursor: progress;",
        "@keyframes share-download-pdf-spin",
        "@media (prefers-reduced-motion: reduce)",
    )

    assert script_tags == ['<script data-skriptoteket-share-pdf-download-controller="owned">']
    assert rendered.rendered_html.count("</script>") == 1
    assert not [expected for expected in expected_html if expected not in rendered.rendered_html]
    assert not [
        forbidden
        for forbidden in ("busyTimeoutMs", "fetch(", "XMLHttpRequest", "console.")
        if forbidden in rendered.rendered_html
    ]
    assert not [expected for expected in expected_css if expected not in rendered.rendered_css]
