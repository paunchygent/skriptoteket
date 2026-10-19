"""Points wording at the non-heading end of an item body.

The end-of-body rule with its segment, gap and picture guards (D6, D7), and
the whole-text one-word-line word keep (D13).
"""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    leftover_points_wording,
    with_settled_points_wording,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording_cuts import (
    body_without_trailing_points,
)
from tests.unit.domain.curated_apps.exam_workspace.points_wording_test_support import (
    _item,
    _paragraph,
    _text,
)


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


def test_one_line_stem_with_other_points_records_the_label() -> None:
    body = (_paragraph(_text("Beskriv processen. (2 p)")),)
    assert leftover_points_wording(body, 3) == "(2 p)"
    item = with_settled_points_wording(_item(body, 3))
    assert item.body == body
    assert item.leftover_points_text == "(2 p)"


def test_single_matching_labels_still_leave() -> None:
    body = (_paragraph(_text("Vilket ord är ett verb? (2 p)")),)
    assert with_settled_points_wording(_item(body, 2)).body == (
        _paragraph(_text("Vilket ord är ett verb?")),
    )
    prose = (_paragraph(_text("Give 3 points of view. (2 p)")),)
    assert with_settled_points_wording(_item(prose, 2)).body == (
        _paragraph(_text("Give 3 points of view.")),
    )


def test_matching_one_word_head_line_leaves_whole_when_other_text_remains() -> None:
    # D8 and review F5: "Max 36p" is a points-only line, so it leaves whole.
    body = (_paragraph(_text("Fråga.")), _paragraph(_text("Max 36p")))
    result = with_settled_points_wording(_item(body, 36))
    assert result.body == (_paragraph(_text("Fråga.")),)
    assert result.leftover_points_text is None


def test_differing_number_keeps_a_one_word_head_line_and_records_it() -> None:
    body = (_paragraph(_text("Fråga.")), _paragraph(_text("Max 36p")))
    result = with_settled_points_wording(_item(body, 30))
    assert result.body == body
    assert result.leftover_points_text == "Max 36p"


def test_whole_text_one_word_head_line_keeps_its_word() -> None:
    # D13: the word stays and only the label leaves, with the blank space.
    assert with_settled_points_wording(_item((_paragraph(_text("Show (2 p)")),), 2)).body == (
        _paragraph(_text("Show")),
    )
    assert with_settled_points_wording(_item((_paragraph(_text("Max 36p")),), 36)).body == (
        _paragraph(_text("Max")),
    )


def test_one_word_head_line_among_other_text_leaves_whole() -> None:
    body = (_paragraph(_text("Beskriv.")), _paragraph(_text("Show (2 p)")))
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == (_paragraph(_text("Beskriv.")),)
    assert result.leftover_points_text is None


def test_whole_text_one_word_head_line_with_other_points_stays_and_records_nothing() -> None:
    # D13 stays gated on D3; a whole-text line never records (D7, N3 A).
    body = (_paragraph(_text("Show (2 p)")),)
    result = with_settled_points_wording(_item(body, 3))
    assert result.body == body
    assert result.leftover_points_text is None


def test_whole_text_bare_label_line_stays() -> None:
    body = (_paragraph(_text("(2 p)")),)
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None
