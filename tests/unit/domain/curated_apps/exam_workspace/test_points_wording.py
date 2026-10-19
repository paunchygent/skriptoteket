"""Trailing points wording leaves an item body when it matches the item's points."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextMark,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    TrailingPoints,
    body_without_trailing_points,
    trailing_points,
    with_settled_points_wording,
    without_trailing_points,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)


def _text(text: str, marks: tuple[NativeTextMark, ...] = ()) -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=marks)


def _paragraph(*segments: NativeSegment) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=tuple(segments))


def _item(body: tuple[NativeParagraph, ...], points: int | float | None) -> NativeExamItem:
    return make_free_text_item().model_copy(update={"body": body, "points": points})


def test_parenthesised_label_ending_the_line_is_found() -> None:
    text = "The school changed ____________ lunch menu. (1 point)"
    assert trailing_points(text) == TrailingPoints(start=text.index(" (1 point)"), value=1)


def test_points_line_is_found_with_the_newline() -> None:
    text = "Dela upp orden.\nPoäng: 6 poäng"
    assert trailing_points(text) == TrailingPoints(start=text.index("\n"), value=6)


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
        ("Svara. (1 poäng)", 1),
        ("Svara (2 p) och motivera.", 2),
        ("Give 3 points of view.", 3),
    ],
)
def test_kept_wording_stays_whole(text: str, points: int | float | None) -> None:
    assert without_trailing_points(text, points) == text


def test_last_paragraph_that_is_only_a_points_line_is_dropped() -> None:
    body = (_paragraph(_text("Vad heter verbet?")), _paragraph(_text("Poäng: 6 poäng")))
    assert body_without_trailing_points(body, 6) == (_paragraph(_text("Vad heter verbet?")),)


def test_wording_in_an_earlier_paragraph_is_not_touched() -> None:
    body = (_paragraph(_text("Poäng: 6 poäng")), _paragraph(_text("Svara utförligt.")))
    assert body_without_trailing_points(body, 6) == body


def test_body_that_is_only_wording_stays() -> None:
    body = (_paragraph(_text("(2 p)")),)
    assert body_without_trailing_points(body, 2) == body


def test_body_left_with_only_blank_text_stays() -> None:
    body = (_paragraph(_text("   ")), _paragraph(_text("Poäng: 6 poäng")))
    assert body_without_trailing_points(body, 6) == body


def test_bold_segment_before_the_cut_keeps_its_marks() -> None:
    body = (
        _paragraph(
            _text("The school changed ____________ lunch menu.", ("bold",)),
            _text(" (1 point)"),
        ),
    )
    assert body_without_trailing_points(body, 1) == (
        _paragraph(_text("The school changed ____________ lunch menu.", ("bold",))),
    )


def test_cut_inside_a_segment_keeps_its_marks() -> None:
    body = (_paragraph(_text("Svara utförligt och tydligt. (2 p)", ("bold",))),)
    assert body_without_trailing_points(body, 2) == (
        _paragraph(_text("Svara utförligt och tydligt.", ("bold",))),
    )


def test_label_spanning_two_segments_leaves_whole() -> None:
    body = (_paragraph(_text("Svara utförligt och tydligt. (2 "), _text("p)")),)
    assert body_without_trailing_points(body, 2) == (
        _paragraph(_text("Svara utförligt och tydligt.")),
    )


def test_paragraph_ending_in_a_gap_is_unchanged() -> None:
    body = (_paragraph(_text("Svara (2 p)"), NativeGapSegment(gap_id="gap_001")),)
    assert body_without_trailing_points(body, 2) == body


def test_paragraph_ending_in_a_picture_is_unchanged() -> None:
    body = (
        _paragraph(_text("Svara (2 p)"), NativeAssetSegment(asset_id="asset_0123456789abcdef")),
    )
    assert body_without_trailing_points(body, 2) == body


def test_points_line_after_a_gap_in_the_same_paragraph_stays() -> None:
    body = (
        _paragraph(
            _text("Läs texten. "),
            NativeGapSegment(gap_id="gap_001"),
            _text("Poäng: 6 poäng"),
        ),
    )
    assert body_without_trailing_points(body, 6) == body


def test_settled_item_loses_matching_wording_and_keeps_points_and_review() -> None:
    item = _item((_paragraph(_text("The school changed ____________ lunch menu. (1 point)")),), 1)
    result = with_settled_points_wording(item)
    assert result.body == (_paragraph(_text("The school changed ____________ lunch menu.")),)
    assert result.points == 1
    assert result.review == item.review


def test_settled_item_loses_matching_decimal_wording() -> None:
    item = _item((_paragraph(_text("Räkna ut svaret. (4,5 p)")),), 4.5)
    result = with_settled_points_wording(item)
    assert result.body == (_paragraph(_text("Räkna ut svaret.")),)
    assert result.points == 4.5


def test_differing_number_keeps_text_and_review_even_when_run_twice() -> None:
    item = _item((_paragraph(_text("Fråga. (3 p)")),), 2)
    result = with_settled_points_wording(item)
    assert result == item
    assert result.review == item.review
    assert with_settled_points_wording(result) == item


def test_missing_points_keeps_text_and_review() -> None:
    item = _item((_paragraph(_text("Fråga. (3 p)")),), None)
    assert with_settled_points_wording(item) == item
