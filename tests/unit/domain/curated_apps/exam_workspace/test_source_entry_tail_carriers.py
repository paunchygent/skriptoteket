"""A native entry continuation never absorbs points or source answer tails."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit


def _as_text(segment: NativeSegment) -> NativeTextSegment:
    assert isinstance(segment, NativeTextSegment)
    return segment


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


@pytest.mark.parametrize("separator", [" ", "\n"])
@pytest.mark.parametrize(
    "tail,facit",
    [
        ("(2 p)", None),
        ("Svar: blue", None),
        ("Svar: blue", "blue"),
    ],
)
def test_bold_final_choice_tail_stays_out_of_the_student_entry(separator, tail, facit):
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue" + separator + tail, marked=True),
    )
    produced = _produced(chunks, facit_text=facit)
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(choice.body).strip() for choice in result.choices] == ["red", "blue"]
    assert body_plain_text(result.body) == "Choose an answer."
    assert result.facit_text == facit
    assert result.points == 2


def test_matching_answer_tail_does_not_join_the_last_right_entry():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "1. red A. warm 2. blue B. cold Svar: 2-B", marked=True),
    )
    produced = _produced(
        chunks,
        kind="matching",
        choices=[],
        match_left=["red", "blue"],
        match_right=["warm", "cold"],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(entry.body).strip() for entry in result.match_left] == ["red", "blue"]
    assert [body_plain_text(entry.body).strip() for entry in result.match_right] == ["warm", "cold"]
    assert result.facit_text is None


def test_ordinary_literal_answer_label_inside_entry_content_survives():
    literal = 'Explain the literal phrase "answer key:" in context.'
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. " + literal, marked=True),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": literal, "correct": False},
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert body_plain_text(result.choices[1].body) == literal
    assert all(
        _as_text(segment).marks == ("bold",) for segment in result.choices[1].body[0].segments
    )


def test_literal_answer_label_in_an_omitted_ordinary_continuation_is_rebuilt():
    literal = 'Explain the literal phrase "answer key:" in context.'
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue\n" + literal, marked=True),
    )
    result = aligned_native_item(
        _produced(chunks), chunks=chunks, language="en", foreign_chunks=()
    ).item
    assert body_plain_text(result.choices[1].body) == "blue\n" + literal


@pytest.mark.parametrize("last_wording", ["blue", "blue Use warm water.", "azure"])
@pytest.mark.parametrize(
    "continuation", ["\nFollow the safety note.\n", " Follow the safety note "]
)
def test_omitted_continuation_before_answer_tail_keeps_visible_text(last_wording, continuation):
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue" + continuation + "Svar: blue", marked=True),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": last_wording, "correct": False},
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue" + continuation.rstrip(),
    ]
    assert all(
        _as_text(segment).marks == ("bold",)
        for paragraph in result.choices[1].body
        for segment in paragraph.segments
    )
    assert result.facit_text is None


def test_numbered_continuation_before_answer_label_keeps_visible_text():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue\nUse cold water. Answer key: blue", marked=True),
    )
    result = aligned_native_item(
        _produced(chunks), chunks=chunks, language="en", foreign_chunks=()
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\nUse cold water.",
    ]
    assert result.facit_text is None


def test_bound_facit_excludes_the_tail_after_an_omitted_continuation():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue\nFollow the safety note.\nSvar: blue", marked=True),
    )
    result = aligned_native_item(
        _produced(chunks, facit_text="blue"), chunks=chunks, language="en", foreign_chunks=()
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\nFollow the safety note.",
    ]
    assert result.facit_text == "blue"


def test_literal_quoted_answer_label_after_a_sentence_stays_in_content():
    literal = 'Read the note. The phrase "answer key:" is literal.'
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue\n" + literal, marked=True),
    )
    result = aligned_native_item(
        _produced(chunks), chunks=chunks, language="en", foreign_chunks=()
    ).item
    assert body_plain_text(result.choices[1].body) == "blue\n" + literal
    assert result.facit_text is None


def test_answer_tail_after_a_quote_closed_before_the_entry_anchor():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", 'A. red B. Say "blue" aloud.\nSvar: blue', marked=True),
    )
    result = aligned_native_item(
        _produced(chunks), chunks=chunks, language="en", foreign_chunks=()
    ).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        'Say "blue" aloud.',
    ]
    assert result.facit_text is None


def test_exact_choice_with_a_literal_label_still_excludes_the_source_tail():
    wording = 'Explain "answer key:" in context.'
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk(
            "body:0002",
            "A. red B. " + wording + "\nFollow the safety note.\nSvar: blue",
            marked=True,
        ),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": wording, "correct": False},
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        wording + "\nFollow the safety note.",
    ]
    assert result.facit_text is None


def test_rewritten_choice_keeps_the_answer_label_the_model_emitted():
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. blue\nUse cold water. Answer key: blue", marked=True),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": "azure Answer key: blue", "correct": False},
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(choice.body) for choice in result.choices] == [
        "red",
        "blue\nUse cold water. Answer key: blue",
    ]
    assert "Answer key: blue" in body_plain_text(result.choices[1].body)
    assert result.facit_text is None


def test_mathematical_point_expression_survives_entry_reconstruction():
    wording = "Calculate (2 p) times q."
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. " + wording, marked=True),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": wording, "correct": False},
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert all(
        _as_text(segment).marks == ("bold",)
        for paragraph in result.choices[1].body
        for segment in paragraph.segments
    )


def test_quoted_point_label_survives_entry_reconstruction():
    wording = 'Explain the notation "(2 p)" in context.'
    chunks = (
        _chunk("body:0001", "Choose an answer."),
        _chunk("body:0002", "A. red B. " + wording, marked=True),
    )
    produced = _produced(
        chunks,
        choices=[
            {"text": "red", "correct": False},
            {"text": wording, "correct": False},
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en", foreign_chunks=()).item
    assert [body_plain_text(choice.body) for choice in result.choices] == ["red", wording]
    assert all(
        _as_text(segment).marks == ("bold",)
        for paragraph in result.choices[1].body
        for segment in paragraph.segments
    )
