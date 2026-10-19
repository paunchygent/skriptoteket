"""String-level points-wording shapes.

``trailing_points`` and ``without_trailing_points`` on strings only: which
endings count as points wording, and which prose mentions never do.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    leftover_points_wording,
    with_settled_points_wording,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording_shapes import (
    TrailingPoints,
    trailing_points,
    without_trailing_points,
)
from tests.unit.domain.curated_apps.exam_workspace.points_wording_test_support import (
    VOLT,
    item,
    paragraph,
    text_segment,
)


def test_parenthesised_label_ending_the_line_is_found() -> None:
    text = "The school changed ____________ lunch menu. (1 point)"
    assert trailing_points(text) == TrailingPoints(
        start=text.index(" (1 point)"), value=1, whole_line=False
    )


def test_points_line_is_found_with_the_newline() -> None:
    text = "Dela upp orden.\nPoäng: 6 poäng"
    assert trailing_points(text) == TrailingPoints(start=text.index("\n"), value=6, whole_line=True)


def test_several_labels_on_one_line_are_not_wording() -> None:
    assert trailing_points("Räkna. (1 p) (2 p)") is None
    assert trailing_points("Räkna. (2 p) (2 p)") is None


@pytest.mark.parametrize(
    "text",
    [
        "Väljer eleven det får den 2 poäng.",
        "Give 3 points of view.",
        "The train leaves at 3 p.m.",
        "Svara (2 p) och motivera.",
        "Read 3 pages.",
    ],
)
def test_prose_that_mentions_points_is_not_wording(text: str) -> None:
    assert trailing_points(text) is None


def test_zero_label_is_not_wording() -> None:
    assert trailing_points("(0 p)") is None


@pytest.mark.parametrize(
    ("text", "points", "expected"),
    [
        (
            "The school changed ____________ lunch menu. (1 point)",
            1,
            "The school changed ____________ lunch menu.",
        ),
        ("Dela upp orden.\nPoäng: 6 poäng", 6, "Dela upp orden."),
        ("Dela upp orden.\nTotalt: 6 p", 6, "Dela upp orden."),
        ("Dela upp orden.\n(1 poäng)", 1, "Dela upp orden."),
        ("Svara utförligt och tydligt.\t(2 p)", 2, "Svara utförligt och tydligt."),
        ("Räkna ut svaret. (4,5 p)", 4.5, "Räkna ut svaret."),
        ("Svara. (1 poäng)", 1, "Svara."),
    ],
)
def test_matching_wording_leaves_the_text(
    text: str, points: int | float | None, expected: str
) -> None:
    assert without_trailing_points(text, points) == expected


@pytest.mark.parametrize(
    ("text", "points"),
    [
        ("Fråga. (3 p)", 2),
        ("Fråga. (3 p)", None),
        ("(2 p)", 2),
        ("Svara (2 p) och motivera.", 2),
        ("Give 3 points of view.", 3),
        ("Räkna. (1 p) (2 p)", 2),
        ("Räkna. (2 p) (2 p)", 2),
    ],
)
def test_kept_wording_stays_whole(text: str, points: int | float | None) -> None:
    assert without_trailing_points(text, points) == text


@pytest.mark.parametrize("points", [4, 5])
def test_volt_question_is_unchanged_and_records_nothing(points: int) -> None:
    body = (paragraph(text_segment(VOLT)),)
    assert trailing_points(VOLT) is None
    assert leftover_points_wording(body, points) is None
    settled = with_settled_points_wording(item(body, points), read_heading_points=None)
    assert settled == item(body, points)


def test_label_on_an_answer_line_is_shape_b_and_leaves_only_the_label() -> None:
    text = "We have alot.\nAnswer: ____________ (1 point)"
    assert trailing_points(text) == TrailingPoints(
        start=text.index(" (1 point)"), value=1, whole_line=False
    )
    assert without_trailing_points(text, 1) == "We have alot.\nAnswer: ____________"


def test_one_line_stem_with_matching_label_leaves_the_stem() -> None:
    assert without_trailing_points("Beskriv processen. (2 p)", 2) == "Beskriv processen."
    assert without_trailing_points("Beskriv processen (2 p)", 2) == "Beskriv processen"
