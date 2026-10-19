"""A score-field line is consumed whole as the points source (TASK-SKRIPT-39-04-20)."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.domain.curated_apps.exam_workspace.test_source_carrier_provenance_repair5 import (
    chunk,
)

pytestmark = pytest.mark.unit

QUESTION = "Beskriv fotosyntesen."
ANSWER_LINE = "________"


def _convert(question, score, *, points, kind=NativeExamItemKind.FREE_TEXT):
    parts = [ANSWER_LINE] if score is None else [ANSWER_LINE, score]
    chunks = tuple(
        chunk(f"body:{index:04d}", text) for index, text in enumerate([question, *parts], start=1)
    )
    produced = ProducedItem(
        source_anchors=tuple(own.anchor for own in chunks),
        outcome="converted",
        review_reason=None,
        kind=kind,
        printed_label=None,
        key_source=None,
        facit_text=None,
        body=(
            ProducedParagraph(
                segments=(ProducedSegment(kind="text", text=question, accepted_values=()),)
            ),
        ),
        points=points,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )
    return aligned_native_item(produced, chunks=chunks, language="sv", foreign_chunks=()).item


@pytest.mark.parametrize(
    ("score", "points"),
    [
        ("/4 p", 4),
        ("/ 4 p", 4),
        ("____ /8 p", 8),
        ("/4 poäng", 4),
        ("  /  4 p  ", 4),
    ],
)
def test_a_score_field_line_is_consumed_whole_and_leaves_no_slash(score, points):
    item = _convert(QUESTION, score, points=points)

    lines = body_text_lines(item.body)
    assert lines == (QUESTION,)
    assert all("/" not in line for line in lines)
    assert item.points == points


def test_a_decimal_score_field_line_is_consumed_whole():
    # free_text rejects fractional points by design (free_text_criteria), so the
    # decimal label variant goes through gap_fill; the carrier seam is kind-agnostic.
    item = _convert(QUESTION, "/4,5 p", points=4.5, kind=NativeExamItemKind.GAP_FILL)

    lines = body_text_lines(item.body)
    assert lines == (QUESTION,)
    assert all("/" not in line for line in lines)
    assert item.points == 4.5


def test_a_score_field_after_question_text_keeps_todays_output():
    item = _convert("Skriv tre ord /4 p", None, points=4)

    assert list(body_text_lines(item.body)) == ["Skriv tre ord /4 p"]
    assert item.points == 4


def test_a_slash_line_without_a_label_stays():
    item = _convert(QUESTION, "/", points=4)

    assert list(body_text_lines(item.body)) == [QUESTION, "/"]
    assert item.points == 4


def test_slashes_elsewhere_in_the_question_stay():
    question = "Förklara verb/nominaliseringar. Välj 1/2 alternativ."
    item = _convert(question, None, points=4)

    assert list(body_text_lines(item.body)) == [question]
    assert item.points == 4


def test_a_score_field_for_other_points_stays_visible():
    item = _convert(QUESTION, "/3 p", points=4)

    assert list(body_text_lines(item.body)) == [QUESTION, "/3 p"]
    assert item.points == 4


def test_a_bare_points_label_still_leaves_no_paragraph():
    item = _convert(QUESTION, "4 p", points=4)

    assert list(body_text_lines(item.body)) == [QUESTION]
    assert item.points == 4
