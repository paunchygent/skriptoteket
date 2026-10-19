"""Points wording in heading paragraphs (D12 heading rules and Correction).

Equal labels ending a heading paragraph leave by their accepted shape only;
sentences and ranges never lose words (R1), a terminal heading keeps its
topic word (R2), and the colon head decides the cut for every label (R3).
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    with_settled_points_wording,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_gap_fill_item,
)
from tests.unit.domain.curated_apps.exam_workspace.points_wording_test_support import (
    _VOLT,
    _heading,
    _heading2,
    _item,
    _paragraph,
    _text,
)


def _uppgift_4_1_body() -> tuple[NativeParagraph, ...]:
    return (
        _paragraph(_text("Läs texterna.")),
        _paragraph(_text("Text A")),
        _paragraph(_text('"Igår kom jag."')),
        _paragraph(_text("Text B")),
        _paragraph(_text('"Ett haveri."')),
        _heading("Jämför texterna (15 p)"),
        _paragraph(_text("Beskriv minst fyra skillnader.")),
    )


def test_mid_body_heading_label_with_equal_points_leaves_only_the_label() -> None:
    # D12 extension (decision A): an equal parenthesised label ending any
    # heading paragraph leaves, with the blank space before it.
    body = _uppgift_4_1_body()
    result = with_settled_points_wording(_item(body, 15))
    assert result.body == (
        _paragraph(_text("Läs texterna.")),
        _paragraph(_text("Text A")),
        _paragraph(_text('"Igår kom jag."')),
        _paragraph(_text("Text B")),
        _paragraph(_text('"Ett haveri."')),
        _heading("Jämför texterna"),
        _paragraph(_text("Beskriv minst fyra skillnader.")),
    )
    assert result.body[5].heading_level == 3
    assert result.leftover_points_text is None


def test_mid_body_heading_label_with_other_points_stays() -> None:
    body = _uppgift_4_1_body()
    result = with_settled_points_wording(_item(body, 12))
    assert result.body == body
    assert result.leftover_points_text is None


def test_mid_body_non_heading_paragraph_is_never_touched() -> None:
    body = (
        _paragraph(_text("Läs texterna.")),
        _paragraph(_text("Text A")),
        _paragraph(_text('"Igår kom jag."')),
        _paragraph(_text("Text B")),
        _paragraph(_text('"Ett haveri."')),
        _paragraph(_text("Jämför texterna (15 p)")),
        _paragraph(_text("Beskriv minst fyra skillnader.")),
    )
    result = with_settled_points_wording(_item(body, 15))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_bare_points_only_line_with_equal_points_is_dropped() -> None:
    # D12 extension (decision A): any points label ending a heading paragraph
    # leaves when its number equals the points.
    body = (_heading("1 point"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 1))
    assert result.body == (_paragraph(_text("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_heading_bare_points_only_line_with_other_points_stays() -> None:
    body = (_heading("1 point"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_bare_label_ending_line_leaves_the_head_trimmed() -> None:
    # The bare label leaves with the blank space before it, plus one trailing
    # dash with its blank space.
    body = (_heading("Uppgift 3 – 4 poäng"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 4))
    assert result.body == (_heading("Uppgift 3"), _paragraph(_text("Svara utförligt.")))
    assert result.body[0].heading_level == 3
    assert result.leftover_points_text is None


def test_heading_bare_label_ending_line_with_other_points_stays() -> None:
    body = (_heading("Uppgift 3 – 4 poäng"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 5))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_headed_points_only_line_with_equal_points_is_dropped() -> None:
    body = (_heading("Poäng: 2 p"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == (_paragraph(_text("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_heading_topic_word_head_keeps_its_word_and_level() -> None:
    # D12 fourth extension: a one-word head without a colon keeps its word;
    # only the label leaves, and the paragraph keeps its heading level.
    body = (_heading("Tempus 3 poäng"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 3))
    assert result.body == (_heading("Tempus"), _paragraph(_text("Svara utförligt.")))
    assert result.body[0].heading_level == 3
    assert result.leftover_points_text is None


def test_heading_topic_word_head_with_other_points_stays() -> None:
    # D12 fourth extension stays gated on D3: a differing number stays.
    body = (_heading("Tempus 3 poäng"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 4))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_colon_head_points_only_line_leaves_whole() -> None:
    # D12 fourth extension: an empty or colon head leaves whole.
    body = (_heading("Poäng: 2 poäng"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == (_paragraph(_text("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_heading_totalt_points_only_line_leaves_whole() -> None:
    # D12 fourth extension: an empty or colon head leaves whole.
    body = (_heading("Totalt: 36 p"), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, 36))
    assert result.body == (_paragraph(_text("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_mid_body_non_heading_bare_label_is_never_touched() -> None:
    body = (
        _paragraph(_text("Läs texterna.")),
        _paragraph(_text("Uppgift 3 – 4 poäng")),
        _paragraph(_text("Beskriv skillnaderna.")),
    )
    result = with_settled_points_wording(_item(body, 4))
    assert result.body == body
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    ("heading", "points"),
    [
        ("Använd mellan 3 poäng och 5 poäng.", 5),
        (_VOLT, 5),
        ("Väljer eleven det får den 2 poäng.", 2),
    ],
)
def test_heading_sentence_or_range_ending_stays_at_equal_points(heading: str, points: int) -> None:
    # D12 Correction (rereview R1): a bare label ending a sentence or a range
    # stays, whatever its number, and records nothing.
    body = (_heading2(heading), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, points))
    assert result.body == body
    assert result.leftover_points_text is None


def test_range_heading_between_paragraphs_stays_at_equal_points() -> None:
    body = (
        _paragraph(_text("Läs texten.")),
        _heading2("Använd mellan 3 poäng och 5 poäng."),
        _paragraph(_text("Svara utförligt.")),
    )
    result = with_settled_points_wording(_item(body, 5))
    assert result.body == body
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    ("body", "points", "expected"),
    [
        (
            (_heading2("Tempus 3 poäng"), _paragraph(_text("Svara utförligt."))),
            3,
            (_heading2("Tempus"), _paragraph(_text("Svara utförligt."))),
        ),
        (
            (
                _paragraph(_text("Läs texten.")),
                _heading2("Tempus 3 poäng"),
                _paragraph(_text("Svara utförligt.")),
            ),
            3,
            (
                _paragraph(_text("Läs texten.")),
                _heading2("Tempus"),
                _paragraph(_text("Svara utförligt.")),
            ),
        ),
        (
            (_paragraph(_text("Läs texten.")), _heading2("Tempus 3 poäng")),
            3,
            (_paragraph(_text("Läs texten.")), _heading2("Tempus")),
        ),
        (
            (_paragraph(_text("Fråga.")), _paragraph(_text("Max 36p"))),
            36,
            (_paragraph(_text("Fråga.")),),
        ),
    ],
)
def test_topic_word_head_keeps_its_word_by_position(
    body: tuple[NativeParagraph, ...],
    points: int,
    expected: tuple[NativeParagraph, ...],
) -> None:
    # D12 Correction (rereview R2): a terminal heading keeps its topic word;
    # D13 whole-line removal applies only to a non-heading last line.
    result = with_settled_points_wording(_item(body, points))
    assert result.body == expected
    assert result.body[0].heading_level == body[0].heading_level
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    "body",
    [
        (
            _paragraph(_text("Poäng: (2 p)")),
            _paragraph(_text("Svara utförligt.")),
        ),
        (
            _heading2("Poäng: (2 p)"),
            _paragraph(_text("Svara utförligt.")),
        ),
    ],
)
def test_colon_head_parenthesised_line_leaves_whole(
    body: tuple[NativeParagraph, ...],
) -> None:
    # D12 Correction (rereview R3): the colon head decides the cut for bare
    # and parenthesised labels alike, in the first paragraph too.
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == (_paragraph(_text("Svara utförligt.")),)
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    ("heading", "points", "expected"),
    [
        ("Uppgift 3 – 4 poäng", 4, "Uppgift 3"),
        ("Uppgift 3: 4 poäng", 4, "Uppgift 3"),
        ("Fråga 2: 1 point", 1, "Fråga 2"),
        ("Jämför texterna (15 p)", 15, "Jämför texterna"),
    ],
)
def test_heading_kept_shapes_still_leave(heading: str, points: int, expected: str) -> None:
    body = (_heading2(heading), _paragraph(_text("Svara utförligt.")))
    result = with_settled_points_wording(_item(body, points))
    assert result.body == (_heading2(expected), _paragraph(_text("Svara utförligt.")))
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    ("terminal", "points", "expected_leftover"),
    [
        ("Svara utförligt och tydligt. (2 p)", 3, "(2 p)"),
        ("Uppgift 3 – 4 poäng", 5, "4 poäng"),
        ("Poäng: 2 poäng", 3, "Poäng: 2 poäng"),
        ("Tempus 3 poäng", 4, "3 poäng"),
        ("Använd mellan 3 poäng och 5 poäng.", 4, None),
        ("Väljer eleven det får den 2 poäng.", 3, None),
    ],
)
def test_terminal_heading_differing_number_records_removable_shape(
    terminal: str, points: int, expected_leftover: str | None
) -> None:
    # D12 Correction: a terminal heading records a differing number for
    # exactly the shapes the heading rule would remove at an equal number;
    # a sentence or range ending is never recorded.
    body = (_paragraph(_text("Läs texten.")), _heading2(terminal))
    result = with_settled_points_wording(_item(body, points))
    assert result.body == body
    assert result.leftover_points_text == expected_leftover


def _gap_heading_body(*segments: NativeSegment) -> tuple[NativeParagraph, ...]:
    return (NativeParagraph(heading_level=2, segments=tuple(segments)),)


def test_terminal_heading_gap_prefix_newline_label_leaves_at_equal_points() -> None:
    # Rereview R5: the gap before the run survives the cut at equal points.
    body = _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), _text("\n(2 p)")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 2})
    )
    assert result.body == _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001")
    )
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


def test_terminal_heading_gap_prefix_newline_label_records_at_other_points() -> None:
    # Rereview R5: the surviving gap keeps the body, so the wording is recorded.
    body = _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), _text("\n(2 p)")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 3})
    )
    assert result.body == body
    assert result.leftover_points_text == "(2 p)"


def test_terminal_heading_picture_prefix_newline_label_leaves_at_equal_points() -> None:
    # Rereview R5: the picture before the run survives the cut at equal points.
    body = _gap_heading_body(
        NativeAssetSegment(asset_id="asset_0123456789abcdef"), _text("\n(2 p)")
    )
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == _gap_heading_body(NativeAssetSegment(asset_id="asset_0123456789abcdef"))
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


def test_terminal_heading_picture_prefix_newline_label_records_at_other_points() -> None:
    # Rereview R5: the surviving picture keeps the body, so the wording is recorded.
    body = _gap_heading_body(
        NativeAssetSegment(asset_id="asset_0123456789abcdef"), _text("\n(2 p)")
    )
    result = with_settled_points_wording(_item(body, 3))
    assert result.body == body
    assert result.leftover_points_text == "(2 p)"


def test_terminal_heading_gap_prefix_bare_label_leaves_at_equal_points() -> None:
    # Rereview R5: the separator and label leave; the text and gap survive.
    body = _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), _text(" – 2 poäng")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 2})
    )
    assert result.body == _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001")
    )
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


def test_terminal_heading_gap_prefix_bare_label_records_at_other_points() -> None:
    # Rereview R5: the surviving gap keeps the body, so the bare label is recorded.
    body = _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), _text(" – 2 poäng")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 3})
    )
    assert result.body == body
    assert result.leftover_points_text == "2 poäng"


@pytest.mark.parametrize("points", [2, 3])
def test_terminal_heading_gap_prefix_inline_label_stays_at_both_numbers(points: int) -> None:
    # The run-boundary guard: a parenthesised label alone in the run with a
    # segment before it is neither removed nor recorded.
    body = _gap_heading_body(
        _text("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), _text(" (2 p)")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": points})
    )
    assert result.body == body
    assert result.leftover_points_text is None
