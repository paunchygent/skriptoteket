"""A printed section total is split over its questions and its points line is no item (D38, D6).

The fresh course-exam recording prints "15 poäng" on the section heading and again on a
points line after the section's fifteenth question. Each of the fifteen questions that
prints no points of its own carries one estimated point, and the points line itself stays
exam-level instruction text with no item.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    build_replay,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_POINTS_LINE = "body:0055"
_POINTS_TEXT = "Poäng: 15 poäng"


def _section_anchors() -> list[str]:
    questions = recording(_EXAM, "docx_grouping_1")["questions"]
    assert isinstance(questions, list)
    anchors: list[str] = []
    for question in questions:
        assert isinstance(question, dict)
        if question["id"] not in {f"q{n}" for n in range(1, 16)}:
            continue
        own = question["anchors"]
        assert isinstance(own, list) and own
        anchors.append(str(own[0]))
    assert len(anchors) == 15
    return anchors


async def test_section_total_is_split_over_its_questions_and_its_points_line_is_no_item():
    replay = build_replay(_EXAM)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    by_anchor = {item.source_anchor: item for item in document.items}
    section = [by_anchor[anchor] for anchor in _section_anchors()]
    assert [item.points for item in section] == [1] * 15
    assert all(item.points_estimated for item in section)
    assert not any(item.review.reasons for item in section)
    assert _POINTS_LINE not in by_anchor
    assert _POINTS_TEXT in body_text_lines(document.instructions)
