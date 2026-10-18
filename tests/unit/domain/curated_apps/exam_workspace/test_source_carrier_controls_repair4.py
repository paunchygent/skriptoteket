"""Adversarial controls for source quote context and structural point classification.

These extend the reviewer probes in ``test_source_entry_tail_carriers`` with the
neighbouring layouts that must survive: same-side Swedish quotes, apostrophes,
a bound facit beside a quoted literal, math expressions whose point-like operand
sits at a line edge, nested or repeated answer tail lines, and prose that ends on
a point-like phrase.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("through_item", [False, True])
def test_quoted_point_content_crossing_source_paragraphs_retains_complete_context(through_item):
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", 'Quote "'),
        _chunk("body:0003", "(2 p)", marked=True),
        _chunk("body:0004", '" here.'),
    )
    if through_item:
        result = aligned_native_item(
            _produced(chunks, kind="free_text", choices=[]), chunks=chunks, language="en"
        ).item.body
    else:
        result = SourceFormatting(chunks).rebuild_body({})
    assert body_plain_text(result) == 'Choose an answer.\nQuote "\n(2 p)\n" here.'


def _chunk(anchor, text, *, marked=False):
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=(DocxSourceRun(0, text, ("bold",) if marked else ()),),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )


def _produced(chunks, *, kind="single_choice", facit_text=None, choices=None, **changes):
    return ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": kind,
            "printed_label": None,
            "points": 2,
            "facit_text": facit_text,
            "key_source": None,
            "body": [
                {"segments": [{"kind": "text", "text": "Choose an answer.", "accepted_values": []}]}
            ],
            "choices": choices
            if choices is not None
            else [{"text": "red", "correct": False}, {"text": "blue", "correct": False}],
            **changes,
        }
    )


def _choice_result(source_text, choices):
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", source_text, marked=True),
    )
    produced = _produced(
        chunks,
        choices=[{"text": text, "correct": False} for text in choices],
    )
    return aligned_native_item(produced, chunks=chunks, language="en").item


def test_curly_quoted_answer_word_keeps_its_closing_quote_before_the_tail():
    result = _choice_result("A. red B. Say “blue” aloud.\nSvar: blue", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "Say “blue” aloud.",
    ]
    assert result.facit_text is None


def test_single_quoted_answer_word_is_not_read_as_an_apostrophe():
    result = _choice_result("A. red B. Say 'blue' aloud.\nSvar: blue", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "Say 'blue' aloud.",
    ]
    assert result.facit_text is None


def test_apostrophe_in_entry_content_opens_no_quote_before_the_tail():
    wording = "Don't hide it."
    result = _choice_result("A. red B. " + wording + "\nSvar: blue", ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert result.facit_text is None


def test_smart_apostrophe_in_entry_content_opens_no_quote_before_the_tail():
    wording = "Don’t hide it."
    result = _choice_result("A. red B. " + wording + "\nSvar: blue", ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert result.facit_text is None


def test_unmatched_inch_quote_does_not_shield_the_answer_tail():
    wording = 'Cut a 5" board.'
    result = _choice_result("A. red B. " + wording + "\nSvar: blue", ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert result.facit_text is None


def test_swedish_smart_quoted_answer_label_stays_visible():
    wording = "Explain ”answer key:” in context."
    result = _choice_result("A. red B. blue\n" + wording + "\nSvar: blue", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\n" + wording,
    ]
    assert result.facit_text is None


def test_swedish_smart_quoted_point_label_survives_reconstruction():
    wording = "”(2 p)”"
    result = _choice_result("A. red B. blue\n" + wording, ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\n" + wording,
    ]


def test_unquoted_literal_label_before_the_real_tail_stays_visible():
    wording = "Write answer key: literally."
    result = _choice_result("A. red B. " + wording + "\nSvar: blue", ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert result.facit_text is None


def test_parenthesized_tail_takes_its_wrapper_with_it():
    result = _choice_result("A. red B. blue (Svar: blue)", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", "blue"]
    assert result.facit_text is None


def test_nested_answer_aliases_leave_one_tail_line():
    result = _choice_result("A. red B. blue\nSvar: Answer key: blue", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", "blue"]
    assert result.facit_text is None


def test_two_answer_tail_lines_leave_the_entry_wording():
    result = _choice_result("A. red B. blue\nSvar: blue\nAnswer key: blue", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", "blue"]
    assert result.facit_text is None


def test_embedded_point_like_phrases_survive_and_only_the_trailing_label_leaves():
    wording = "Calculate (2 p) times q."
    result = _choice_result("A. red B. " + wording + " (2 p)", ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert all(
        segment.marks == ("bold",)
        for paragraph in result.choices[1].body
        for segment in paragraph.segments
    )


def test_point_like_prose_between_words_survives_reconstruction():
    wording = "Use 2 points and 3 points carefully."
    result = _choice_result("A. red B. " + wording, ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]


def test_point_like_prose_at_a_sentence_end_survives_reconstruction():
    wording = "Explain why the team earned 2 points."
    result = _choice_result("A. red B. " + wording, ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]


def test_single_quoted_point_literal_survives_reconstruction():
    wording = "Explain the notation '(2 p)' here."
    result = _choice_result("A. red B. " + wording, ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]


@pytest.mark.parametrize("facit", [None, "blue", "red"])
def test_quoted_literal_answer_label_survives_with_and_without_a_bound_facit(facit):
    wording = 'Explain "Answer key: blue" in context.'
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. " + wording + "\nSvar: red", marked=True),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": wording, "correct": False},
        ],
        facit_text=facit,
    )
    result = aligned_native_item(produced, chunks=chunks, language="en").item
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert result.facit_text == facit


def test_body_rebuild_keeps_point_like_mathematical_content():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "Calculate (2 p) times q.", marked=True),
    )
    result = SourceFormatting(chunks).rebuild_body({})
    assert body_plain_text(result) == "Choose an answer.\nCalculate (2 p) times q."


def test_body_rebuild_keeps_short_mathematical_content():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "(2 p) times q.", marked=True),
    )
    result = SourceFormatting(chunks).rebuild_body({})
    assert body_plain_text(result) == "Choose an answer.\n(2 p) times q."


def test_source_only_rebuild_keeps_points_without_a_native_field():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "Total: 38 poäng", marked=True),
    )
    result = SourceFormatting(chunks).rebuild_body({})
    assert body_plain_text(result) == "Choose an answer.\nTotal: 38 poäng"


def test_recovered_matching_score_before_a_continuation_is_metadata():
    result = _choice_result("A. red B. blue\n(2 p) times q.", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\n times q.",
    ]


def test_recovered_matching_score_before_an_operand_is_metadata():
    result = _choice_result("A. red B. blue\n(2 p) q.", ["red", "blue"])
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\n q.",
    ]


def test_trailing_mathematical_point_expression_survives():
    wording = "Calculate q times (2 p)."
    result = _choice_result("A. red B. " + wording, ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]


def test_multiplication_symbols_keep_point_like_expressions_visible():
    wording = "(2 p) × q."
    result = _choice_result("A. red B. " + wording, ["red", wording])
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]


def test_detached_score_after_a_complete_sentence_is_an_annotation():
    wording = "Explain the idea."
    result = _choice_result("A. red B. " + wording + " (2 p).", ["red", wording])
    visible = body_plain_text(result.choices[1].body)
    assert "(2 p)" not in visible
    assert wording in visible
