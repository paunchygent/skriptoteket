"""Points lines judged against real corpus chunks."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    points_line,
    points_only_line,
    printed_points,
    with_printed_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
)


@pytest.mark.parametrize(
    ("docx", "anchor"),
    [
        ("svenska_2_grammatik_omprov_variant_1_med_facit", "body:0004"),
        ("svenska_2_grammatik_omprov_variant_1_med_facit", "body:0013"),
        ("bf26_diagnostic_grammar_test_ht26_med_facit", "body:0003"),
        ("bf26_english_1_unit_test_kap_1_2_med_facit", "body:0003"),
    ],
)
def test_total_and_points_lines_are_points_lines(docx: str, anchor: str):
    text = chunks_by_anchor(docx)[anchor].text
    assert text.startswith(("Total:", "Poäng:"))
    assert points_line(text)


@pytest.mark.parametrize(
    ("docx", "anchor"),
    [
        ("bf26_english_1_unit_test_kap_1_2_med_facit", "body:0058"),
        ("chapter_4_poetry_and_lyrics_quiz_med_facit", "body:0129"),
    ],
)
def test_sentence_or_heading_that_mentions_points_is_not_a_points_line(docx: str, anchor: str):
    text = chunks_by_anchor(docx)[anchor].text
    assert "point" in text
    assert not points_line(text)


@pytest.mark.parametrize(
    ("text", "points"),
    [
        ("3 p", 3),
        ("3 p.", 3),
        ("(3 p)", 3),
        ("(3 pt.)", 3),
        ("36 pts", 36),
        ("3 point", 3),
        ("3 points", 3),
        ("3 poäng", 3),
        ("Totalt: 36 p", 36),
        ("Max 36p", 36),
        ("Totalt: 7,5 p", 7.5),
        ("Totalt: 7.5 p", 7.5),
        ("The train leaves at 3 p.m. Translate the sentence.", None),
        ("p. 3", None),
        ("Read 3 pages.", None),
        ("Give 3 points of view.", None),
        ("Svara 2 p snabbt.", None),
        ("The train leaves at 3 p.m. (2 p)", 2),
    ],
)
def test_only_complete_points_units_supply_points_and_leave_the_text(
    text: str, points: int | float | None
) -> None:
    own = (DocxChunk(anchor="body:0001", kind="paragraph", text=text, marked_text=text),)
    item = ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.FREE_TEXT,
        printed_label=None,
        key_source=None,
        facit_text=None,
        body=(
            ProducedParagraph(
                segments=(ProducedSegment(kind="text", text=text, accepted_values=()),)
            ),
        ),
        points=None,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )

    assert printed_points(own) == points
    result = with_printed_points(item, own)
    assert result.points == points
    assert result.body[0].segments[0].text == text


def test_bare_label_followed_by_words_is_not_a_points_line() -> None:
    assert not points_line("Give 3 points of view.")


@pytest.mark.parametrize(
    "text",
    ["Poäng: 6 poäng", "Totalt: 6 p", "6 p", "(2 p)", "Max 36p", "Max poäng: 6 p"],
)
def test_short_label_lines_are_points_only_lines(text: str) -> None:
    assert points_only_line(text)


@pytest.mark.parametrize(
    "text",
    [
        "Answer: ____________ (1 point)",
        "Svar: ______ (2 p)",
        "Beskriv processen. (2 p)",
        "Beskriv processen (2 p)",
        "Give 3 points of view.",
    ],
)
def test_stem_and_answer_lines_are_not_points_only_lines(text: str) -> None:
    assert not points_only_line(text)


def test_a_reply_without_points_keeps_every_body_segment_text() -> None:
    """D8: ``with_printed_points`` reads the points and leaves the text (D1).

    Trailing wording is settled later on the final item, after every points
    source has run, so the reply body reaches the gate untouched.
    """
    own = (DocxChunk(anchor="body:0001", kind="paragraph", text="(2 p)", marked_text="(2 p)"),)
    item = ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.FREE_TEXT,
        printed_label=None,
        key_source=None,
        facit_text=None,
        body=(
            ProducedParagraph(
                segments=(
                    ProducedSegment(kind="text", text="Svara utförligt. ", accepted_values=()),
                    ProducedSegment(kind="text", text="(2 p)", accepted_values=()),
                )
            ),
        ),
        points=None,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )

    result = with_printed_points(item, own)

    assert result.points == 2
    assert [segment.text for segment in result.body[0].segments] == [
        "Svara utförligt. ",
        "(2 p)",
    ]
