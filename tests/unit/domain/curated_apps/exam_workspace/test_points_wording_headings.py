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
    VOLT,
    heading,
    heading2,
    item,
    paragraph,
    text_segment,
)


def _uppgift_4_1_body() -> tuple[NativeParagraph, ...]:
    return (
        paragraph(text_segment("Läs texterna.")),
        paragraph(text_segment("Text A")),
        paragraph(text_segment('"Igår kom jag."')),
        paragraph(text_segment("Text B")),
        paragraph(text_segment('"Ett haveri."')),
        heading("Jämför texterna (15 p)"),
        paragraph(text_segment("Beskriv minst fyra skillnader.")),
    )


def test_mid_body_heading_label_with_equal_points_leaves_only_the_label() -> None:
    # D12 extension (decision A): an equal parenthesised label ending any
    # heading paragraph leaves, with the blank space before it.
    body = _uppgift_4_1_body()
    result = with_settled_points_wording(item(body, 15))
    assert result.body == (
        paragraph(text_segment("Läs texterna.")),
        paragraph(text_segment("Text A")),
        paragraph(text_segment('"Igår kom jag."')),
        paragraph(text_segment("Text B")),
        paragraph(text_segment('"Ett haveri."')),
        heading("Jämför texterna"),
        paragraph(text_segment("Beskriv minst fyra skillnader.")),
    )
    assert result.body[5].heading_level == 3
    assert result.leftover_points_text is None


def test_mid_body_heading_label_with_other_points_stays() -> None:
    body = _uppgift_4_1_body()
    result = with_settled_points_wording(item(body, 12))
    assert result.body == body
    assert result.leftover_points_text is None


def test_mid_body_non_heading_paragraph_is_never_touched() -> None:
    body = (
        paragraph(text_segment("Läs texterna.")),
        paragraph(text_segment("Text A")),
        paragraph(text_segment('"Igår kom jag."')),
        paragraph(text_segment("Text B")),
        paragraph(text_segment('"Ett haveri."')),
        paragraph(text_segment("Jämför texterna (15 p)")),
        paragraph(text_segment("Beskriv minst fyra skillnader.")),
    )
    result = with_settled_points_wording(item(body, 15))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_bare_points_only_line_with_equal_points_is_dropped() -> None:
    # D12 extension (decision A): any points label ending a heading paragraph
    # leaves when its number equals the points.
    body = (heading("1 point"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 1))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_heading_bare_points_only_line_with_other_points_stays() -> None:
    body = (heading("1 point"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_bare_label_ending_line_leaves_the_head_trimmed() -> None:
    # The bare label leaves with the blank space before it, plus one trailing
    # dash with its blank space.
    body = (heading("Uppgift 3 – 4 poäng"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 4))
    assert result.body == (heading("Uppgift 3"), paragraph(text_segment("Svara utförligt.")))
    assert result.body[0].heading_level == 3
    assert result.leftover_points_text is None


def test_heading_bare_label_ending_line_with_other_points_stays() -> None:
    body = (heading("Uppgift 3 – 4 poäng"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 5))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_headed_points_only_line_with_equal_points_is_dropped() -> None:
    body = (heading("Poäng: 2 p"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 2))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_heading_topic_word_head_keeps_its_word_and_level() -> None:
    # D12 fourth extension: a one-word head without a colon keeps its word;
    # only the label leaves, and the paragraph keeps its heading level.
    body = (heading("Tempus 3 poäng"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 3))
    assert result.body == (heading("Tempus"), paragraph(text_segment("Svara utförligt.")))
    assert result.body[0].heading_level == 3
    assert result.leftover_points_text is None


def test_heading_topic_word_head_with_other_points_stays() -> None:
    # D12 fourth extension stays gated on D3: a differing number stays.
    body = (heading("Tempus 3 poäng"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 4))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_colon_head_points_only_line_leaves_whole() -> None:
    # D12 fourth extension: an empty or colon head leaves whole.
    body = (heading("Poäng: 2 poäng"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 2))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_heading_totalt_points_only_line_leaves_whole() -> None:
    # D12 fourth extension: an empty or colon head leaves whole.
    body = (heading("Totalt: 36 p"), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 36))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_mid_body_non_heading_bare_label_is_never_touched() -> None:
    body = (
        paragraph(text_segment("Läs texterna.")),
        paragraph(text_segment("Uppgift 3 – 4 poäng")),
        paragraph(text_segment("Beskriv skillnaderna.")),
    )
    result = with_settled_points_wording(item(body, 4))
    assert result.body == body
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    ("heading", "points"),
    [
        ("Använd mellan 3 poäng och 5 poäng.", 5),
        (VOLT, 5),
        ("Väljer eleven det får den 2 poäng.", 2),
    ],
)
def test_heading_sentence_or_range_ending_stays_at_equal_points(heading: str, points: int) -> None:
    # D12 Correction (rereview R1): a bare label ending a sentence or a range
    # stays, whatever its number, and records nothing.
    body = (heading2(heading), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, points))
    assert result.body == body
    assert result.leftover_points_text is None


def test_range_heading_between_paragraphs_stays_at_equal_points() -> None:
    body = (
        paragraph(text_segment("Läs texten.")),
        heading2("Använd mellan 3 poäng och 5 poäng."),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 5))
    assert result.body == body
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    ("body", "points", "expected"),
    [
        (
            (heading2("Tempus 3 poäng"), paragraph(text_segment("Svara utförligt."))),
            3,
            (heading2("Tempus"), paragraph(text_segment("Svara utförligt."))),
        ),
        (
            (
                paragraph(text_segment("Läs texten.")),
                heading2("Tempus 3 poäng"),
                paragraph(text_segment("Svara utförligt.")),
            ),
            3,
            (
                paragraph(text_segment("Läs texten.")),
                heading2("Tempus"),
                paragraph(text_segment("Svara utförligt.")),
            ),
        ),
        (
            (paragraph(text_segment("Läs texten.")), heading2("Tempus 3 poäng")),
            3,
            (paragraph(text_segment("Läs texten.")), heading2("Tempus")),
        ),
        (
            (paragraph(text_segment("Fråga.")), paragraph(text_segment("Max 36p"))),
            36,
            (paragraph(text_segment("Fråga.")),),
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
    result = with_settled_points_wording(item(body, points))
    assert result.body == expected
    assert result.body[0].heading_level == body[0].heading_level
    assert result.leftover_points_text is None


@pytest.mark.parametrize(
    "body",
    [
        (
            paragraph(text_segment("Poäng: (2 p)")),
            paragraph(text_segment("Svara utförligt.")),
        ),
        (
            heading2("Poäng: (2 p)"),
            paragraph(text_segment("Svara utförligt.")),
        ),
    ],
)
def test_colon_head_parenthesised_line_leaves_whole(
    body: tuple[NativeParagraph, ...],
) -> None:
    # D12 Correction (rereview R3): the colon head decides the cut for bare
    # and parenthesised labels alike, in the first paragraph too.
    result = with_settled_points_wording(item(body, 2))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
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
    body = (heading2(heading), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, points))
    assert result.body == (heading2(expected), paragraph(text_segment("Svara utförligt.")))
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
    body = (paragraph(text_segment("Läs texten.")), heading2(terminal))
    result = with_settled_points_wording(item(body, points))
    assert result.body == body
    assert result.leftover_points_text == expected_leftover


def _gap_heading_body(*segments: NativeSegment) -> tuple[NativeParagraph, ...]:
    return (NativeParagraph(heading_level=2, segments=tuple(segments)),)


def test_terminal_heading_gap_prefix_newline_label_leaves_at_equal_points() -> None:
    # Rereview R5: the gap before the run survives the cut at equal points.
    body = _gap_heading_body(
        text_segment("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), text_segment("\n(2 p)")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 2})
    )
    assert result.body == _gap_heading_body(
        text_segment("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001")
    )
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


def test_terminal_heading_gap_prefix_newline_label_records_at_other_points() -> None:
    # Rereview R5: the surviving gap keeps the body, so the wording is recorded.
    body = _gap_heading_body(
        text_segment("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), text_segment("\n(2 p)")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 3})
    )
    assert result.body == body
    assert result.leftover_points_text == "(2 p)"


def test_terminal_heading_picture_prefix_newline_label_leaves_at_equal_points() -> None:
    # Rereview R5: the picture before the run survives the cut at equal points.
    body = _gap_heading_body(
        NativeAssetSegment(asset_id="asset_0123456789abcdef"), text_segment("\n(2 p)")
    )
    result = with_settled_points_wording(item(body, 2))
    assert result.body == _gap_heading_body(NativeAssetSegment(asset_id="asset_0123456789abcdef"))
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


def test_terminal_heading_picture_prefix_newline_label_records_at_other_points() -> None:
    # Rereview R5: the surviving picture keeps the body, so the wording is recorded.
    body = _gap_heading_body(
        NativeAssetSegment(asset_id="asset_0123456789abcdef"), text_segment("\n(2 p)")
    )
    result = with_settled_points_wording(item(body, 3))
    assert result.body == body
    assert result.leftover_points_text == "(2 p)"


def test_terminal_heading_gap_prefix_bare_label_leaves_at_equal_points() -> None:
    # Rereview R5: the separator and label leave; the text and gap survive.
    body = _gap_heading_body(
        text_segment("Skriv rätt ord "),
        NativeGapSegment(gap_id="gap_001"),
        text_segment(" – 2 poäng"),
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": 2})
    )
    assert result.body == _gap_heading_body(
        text_segment("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001")
    )
    assert result.body[0].heading_level == 2
    assert result.leftover_points_text is None


def test_terminal_heading_gap_prefix_bare_label_records_at_other_points() -> None:
    # Rereview R5: the surviving gap keeps the body, so the bare label is recorded.
    body = _gap_heading_body(
        text_segment("Skriv rätt ord "),
        NativeGapSegment(gap_id="gap_001"),
        text_segment(" – 2 poäng"),
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
        text_segment("Skriv rätt ord "), NativeGapSegment(gap_id="gap_001"), text_segment(" (2 p)")
    )
    result = with_settled_points_wording(
        make_gap_fill_item().model_copy(update={"body": body, "points": points})
    )
    assert result.body == body
    assert result.leftover_points_text is None
