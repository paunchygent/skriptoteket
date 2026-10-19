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
    leftover_points_wording,
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


def _heading(text: str, level: int = 3) -> NativeParagraph:
    return NativeParagraph(heading_level=level, segments=(_text(text),))


def _item(body: tuple[NativeParagraph, ...], points: int | float | None) -> NativeExamItem:
    return make_free_text_item().model_copy(update={"body": body, "points": points})


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
    assert result.body == item.body
    assert result.points == item.points
    assert result.review == item.review
    assert result.leftover_points_text == "(3 p)"
    second = with_settled_points_wording(result)
    assert second.body == item.body
    assert second.points == item.points
    assert second.review == item.review
    assert second.leftover_points_text == "(3 p)"


def test_missing_points_keeps_text_and_review() -> None:
    item = _item((_paragraph(_text("Fråga. (3 p)")),), None)
    assert with_settled_points_wording(item) == item


def test_differing_number_keeps_the_body_and_records_the_points_line() -> None:
    body = (_paragraph(_text("Dela upp orden.\nPoäng: 4 poäng")),)
    assert leftover_points_wording(body, 6) == "Poäng: 4 poäng"
    item = with_settled_points_wording(_item(body, 6))
    assert item.body == body
    assert item.leftover_points_text == "Poäng: 4 poäng"


def test_differing_number_keeps_the_body_and_records_the_parenthesised_label() -> None:
    body = (_paragraph(_text("The school changed ____________ lunch menu. (2 points)")),)
    assert leftover_points_wording(body, 1) == "(2 points)"
    item = with_settled_points_wording(_item(body, 1))
    assert item.body == body
    assert item.leftover_points_text == "(2 points)"


def test_equal_number_cuts_the_body_and_records_nothing() -> None:
    body = (_paragraph(_text("Dela upp orden.\nPoäng: 6 poäng")),)
    assert leftover_points_wording(body, 6) is None
    item = with_settled_points_wording(_item(body, 6))
    assert item.body == (_paragraph(_text("Dela upp orden.")),)
    assert item.leftover_points_text is None


def test_nothing_is_recorded_without_points() -> None:
    body = (_paragraph(_text("Fråga. (3 p)")),)
    assert leftover_points_wording(body, None) is None
    assert with_settled_points_wording(_item(body, None)).leftover_points_text is None


def test_whole_stem_wording_is_never_recorded() -> None:
    body = (_paragraph(_text("(2 p)")),)
    assert leftover_points_wording(body, 3) is None
    assert with_settled_points_wording(_item(body, 3)).leftover_points_text is None


def test_mid_text_label_is_never_recorded() -> None:
    body = (_paragraph(_text("Svara (2 p) och motivera.")),)
    assert leftover_points_wording(body, 3) is None
    assert with_settled_points_wording(_item(body, 3)) == _item(body, 3)


def test_gap_ending_paragraph_records_nothing() -> None:
    body = (_paragraph(_text("Svara (2 p)"), NativeGapSegment(gap_id="gap_001")),)
    assert leftover_points_wording(body, 3) is None
    assert with_settled_points_wording(_item(body, 3)) == _item(body, 3)


def test_picture_ending_paragraph_records_nothing() -> None:
    body = (
        _paragraph(_text("Svara (2 p)"), NativeAssetSegment(asset_id="asset_0123456789abcdef")),
    )
    assert leftover_points_wording(body, 3) is None
    assert with_settled_points_wording(_item(body, 3)) == _item(body, 3)


_VOLT = (
    "Pelle gör en fin volt, Sara gör en ful. Sätt poäng på Sara och Pelles volter. "
    "Använd mellan 3 poäng och 5 poäng."
)


@pytest.mark.parametrize("points", [4, 5])
def test_volt_question_is_unchanged_and_records_nothing(points: int) -> None:
    body = (_paragraph(_text(_VOLT)),)
    assert trailing_points(_VOLT) is None
    assert leftover_points_wording(body, points) is None
    assert with_settled_points_wording(_item(body, points)) == _item(body, points)


def test_settled_item_is_idempotent_and_keeps_points_and_review() -> None:
    body = (_paragraph(_text("Svara utförligt och tydligt. (3 p)")),)
    item = _item(body, 2)
    once = with_settled_points_wording(item)
    assert once.leftover_points_text == "(3 p)"
    assert once.points == 2
    assert once.review == item.review
    assert with_settled_points_wording(once) == once


def test_label_on_an_answer_line_is_shape_b_and_leaves_only_the_label() -> None:
    text = "We have alot.\nAnswer: ____________ (1 point)"
    assert trailing_points(text) == TrailingPoints(
        start=text.index(" (1 point)"), value=1, whole_line=False
    )
    assert without_trailing_points(text, 1) == "We have alot.\nAnswer: ____________"


def test_one_line_stem_with_matching_label_leaves_the_stem() -> None:
    assert without_trailing_points("Beskriv processen. (2 p)", 2) == "Beskriv processen."
    assert without_trailing_points("Beskriv processen (2 p)", 2) == "Beskriv processen"


def test_one_line_stem_with_other_points_records_the_label() -> None:
    body = (_paragraph(_text("Beskriv processen. (2 p)")),)
    assert leftover_points_wording(body, 3) == "(2 p)"
    item = with_settled_points_wording(_item(body, 3))
    assert item.body == body
    assert item.leftover_points_text == "(2 p)"


def test_first_paragraph_heading_label_leaves_and_keeps_its_level() -> None:
    body = (
        _heading("5. Resor till skolan (1 poäng)"),
        _paragraph(_text("En grupp skriver om hur elever tar sig till skolan.")),
    )
    result = with_settled_points_wording(_item(body, 1))
    assert result.body[0].heading_level == 3
    assert result.body[0] == _heading("5. Resor till skolan")
    assert result.body[1:] == body[1:]
    assert result.points == 1
    assert result.leftover_points_text is None


def test_first_paragraph_non_heading_label_leaves() -> None:
    body = (
        _paragraph(_text("1. Select the word or phrase for each definition. (3 points)")),
        _paragraph(_text("Write the letter of the matching option.")),
        _paragraph(_text("1. absence from school | ____ | A. truancy")),
    )
    result = with_settled_points_wording(_item(body, 3))
    assert result.body[0] == _paragraph(_text("1. Select the word or phrase for each definition."))
    assert result.body[1:] == body[1:]
    assert result.leftover_points_text is None


def test_first_paragraph_multiline_label_leaves_the_text_before_it() -> None:
    first = (
        "1. Milan tends to boast when he meets new teammates.\n\n"
        "What does boast mean here? (1 point)"
    )
    body = (_paragraph(_text(first)), _paragraph(_text("A. skryta")))
    result = with_settled_points_wording(_item(body, 1))
    assert result.body[0] == _paragraph(
        _text("1. Milan tends to boast when he meets new teammates.\n\nWhat does boast mean here?")
    )
    assert result.body[1:] == body[1:]


def test_first_paragraph_differing_number_stays_and_records_nothing() -> None:
    body = (
        _paragraph(_text("2. Tidningsartiklar (2 poäng)")),
        _paragraph(_text("Svara utförligt.")),
    )
    result = with_settled_points_wording(_item(body, 3))
    assert result.body == body
    assert result.points == 3
    assert result.leftover_points_text is None


def test_first_paragraph_label_without_points_is_untouched() -> None:
    body = (
        _paragraph(_text("2. Tidningsartiklar (2 poäng)")),
        _paragraph(_text("Svara utförligt.")),
    )
    assert with_settled_points_wording(_item(body, None)) == _item(body, None)


def test_first_paragraph_in_sentence_label_is_untouched() -> None:
    body = (
        _paragraph(_text("Svara (2 p) och motivera.")),
        _paragraph(_text("Fortsätt här.")),
    )
    assert with_settled_points_wording(_item(body, 2)) == _item(body, 2)


def test_first_paragraph_points_line_is_not_this_rules_case() -> None:
    body = (
        _paragraph(_text("Poäng: 2 poäng")),
        _paragraph(_text("Svara utförligt.")),
    )
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_ending_in_a_gap_is_untouched() -> None:
    body = (
        _paragraph(_text("Svara (2 p)"), NativeGapSegment(gap_id="gap_001")),
        _paragraph(_text("Fortsätt här.")),
    )
    assert with_settled_points_wording(_item(body, 2)) == _item(body, 2)


def test_first_paragraph_volt_question_is_untouched() -> None:
    body = (_paragraph(_text(_VOLT)), _paragraph(_text("Fortsätt här.")))
    result = with_settled_points_wording(_item(body, 5))
    assert result.body == body
    assert result.leftover_points_text is None


def test_settled_item_with_two_labels_on_one_line_keeps_everything() -> None:
    for text in ("Räkna. (1 p) (2 p)", "Räkna. (2 p) (2 p)"):
        body = (_paragraph(_text(text)),)
        item = with_settled_points_wording(_item(body, 2))
        assert item.body == body
        assert item.leftover_points_text is None


def test_settled_item_with_two_points_lines_keeps_everything_and_is_idempotent() -> None:
    body = (
        _paragraph(_text("Fråga.")),
        _paragraph(_text("Poäng: 2 poäng")),
        _paragraph(_text("Poäng: 2 poäng")),
    )
    once = with_settled_points_wording(_item(body, 2))
    assert once.body == body
    assert once.leftover_points_text is None
    assert with_settled_points_wording(once) == once


def test_settled_item_with_a_label_at_each_end_keeps_everything() -> None:
    body = (
        _paragraph(_text("Fråga. (2 p)")),
        _paragraph(_text("Avslutning. (3 p)")),
    )
    item = with_settled_points_wording(_item(body, 2))
    assert item.body == body
    assert item.leftover_points_text is None


def test_single_matching_labels_still_leave() -> None:
    body = (_paragraph(_text("Vilket ord är ett verb? (2 p)")),)
    assert with_settled_points_wording(_item(body, 2)).body == (
        _paragraph(_text("Vilket ord är ett verb?")),
    )
    prose = (_paragraph(_text("Give 3 points of view. (2 p)")),)
    assert with_settled_points_wording(_item(prose, 2)).body == (
        _paragraph(_text("Give 3 points of view.")),
    )


def test_matching_labels_at_both_ends_leave_and_settling_is_idempotent() -> None:
    # D3 (with several labels nothing is removed) and review F3: an item
    # whose body holds more than one points label keeps both labels.
    body = (
        _paragraph(_text("Frågan inleds här. (2 p)")),
        _paragraph(_text("Frågan avslutas här. (2 p)")),
    )
    once = with_settled_points_wording(_item(body, 2))
    assert once.body == body
    assert once.leftover_points_text is None
    assert with_settled_points_wording(once) == once
