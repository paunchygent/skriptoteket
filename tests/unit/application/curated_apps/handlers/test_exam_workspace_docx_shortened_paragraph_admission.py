"""A shortened own paragraph shows its whole own source paragraph (TASK-SKRIPT-REP-0049).

An exact first-sentence-only reply shows the whole own paragraph with its source marks;
a reworded reply, a facit-shown remainder, a blank-run remainder, an inline answer label,
a choice-shown remainder, a jointly covered split, and a gap paragraph all keep the
model's wording with no left-out mark.
"""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import FORMATTING_REASON

pytestmark = pytest.mark.unit


def _runs_chunk(anchor: str, runs: tuple[tuple[str, tuple[str, ...]], ...]) -> DocxChunk:
    offset = 0
    spans = []
    for text, marks in runs:
        spans.append(DocxSourceRun(offset=offset, text=text, marks=marks))
        offset += len(text)
    text = "".join(run.text for run in spans)
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=tuple(spans),
        paragraphs=(DocxSourceParagraph(offset=0, text=text, heading_level=None),),
    )


def _table_chunk(anchor: str, *cells: str) -> DocxChunk:
    text = " | ".join(cells)
    paragraphs = []
    offset = 0
    for cell in cells:
        paragraphs.append(DocxSourceParagraph(offset=offset, text=cell, heading_level=None))
        offset += len(cell) + len(" | ")
    return DocxChunk(anchor, "table", text, text, paragraphs=tuple(paragraphs))


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _gap(*values: str) -> dict[str, JsonValue]:
    return {"kind": "gap", "text": None, "accepted_values": list(values)}


def _choice(text: str, correct: bool) -> dict[str, JsonValue]:
    return {"text": text, "correct": correct}


def _item(
    anchors: tuple[str, ...],
    label: str | None,
    body: list[list[JsonValue]],
    *,
    kind: str = "free_text",
    key_source: str | None = None,
    facit_text: str | None = None,
    choices: list[JsonValue] | None = None,
    points: int = 2,
) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": kind,
        "key_source": key_source,
        "facit_text": facit_text,
        "printed_label": label,
        "body": [{"segments": segments} for segments in body],
        "points": points,
        "choices": choices if choices is not None else [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _state(*chunks: DocxChunk) -> DocxBuildState:
    return DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(chunk.anchor for chunk in chunks),),
    )


def _admit(chunks: tuple[DocxChunk, ...], item: dict[str, JsonValue]):
    state = _state(*chunks)
    admit_batch({"items": [item]}, state)
    return _accepted(state)


def _accepted(state: DocxBuildState):
    (aligned, _) = state.accepted[0]
    assert aligned.item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [event for event in state.events if event.code == "own_chunks_left_out"] == []
    return aligned.item


def _reviewed(state: DocxBuildState):
    (aligned, _) = state.accepted[0]
    assert aligned.item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert aligned.item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert aligned.item.review.reasons == (FORMATTING_REASON,)
    assert [event for event in state.events if event.code == "formatting_transfer_failed"] != []
    return aligned.item


def test_a_question_sentence_the_facit_repeats_goes_to_source_review_with_its_text():
    chunks = (_chunk("body:0001", "2. A coin was tossed twice. Determine the number of outcomes."),)
    state = _state(*chunks)
    admit_batch(
        {
            "items": [
                _item(
                    ("body:0001",),
                    "2",
                    [[_text("Determine the number of outcomes.")]],
                    facit_text="A coin was tossed twice. There are four possible outcomes.",
                )
            ]
        },
        state,
    )
    item = _reviewed(state)
    assert "A coin was tossed twice. Determine the number of outcomes." in body_plain_text(
        item.body
    )


def test_a_gap_instruction_the_facit_repeats_goes_to_source_review_with_its_text():
    chunks = (_chunk("body:0001", "2. Read the passage. Water is ____."),)
    state = _state(*chunks)
    admit_batch(
        {
            "items": [
                _item(
                    ("body:0001",),
                    "2",
                    [[_text("Water is "), _gap("a liquid"), _text(".")]],
                    kind="gap_fill",
                    key_source="copied",
                    facit_text="Read the passage. Water is a liquid.",
                )
            ]
        },
        state,
    )
    item = _reviewed(state)
    assert "Read the passage." in body_plain_text(item.body)


def test_an_exact_first_sentence_only_reply_shows_the_whole_own_paragraph_with_its_marks():
    chunks = (
        _runs_chunk(
            "body:0001",
            (("2. Alpha ", ()), ("marked", ("bold",)), (" first. Beta second. (2 p)", ())),
        ),
    )
    item = _admit(chunks, _item(("body:0001",), "2", [[_text("Alpha marked first.")]]))
    assert body_plain_text(item.body) == "Alpha marked first. Beta second."
    marks = [
        (segment.text, segment.marks)
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]
    assert ("marked", ("bold",)) in marks


def test_a_reworded_reply_keeps_the_models_wording_without_a_left_out_mark():
    # The reply rewords the first sentence and leaves out the second: the aligned path keeps
    # the model's wording, so no restore and no left-out mark follow (D3).
    chunks = (_chunk("body:0001", "Förklara hur vatten blir ånga. Ge ett exempel från köket."),)
    item = _admit(chunks, _item(("body:0001",), "1", [[_text("Förklara hur ånga bildas.")]]))
    assert body_plain_text(item.body) == "Förklara hur ånga bildas."


def test_a_remainder_the_facit_repeats_goes_to_source_review_with_its_text():
    chunks = (_chunk("body:0001", "2. Klassen läste inte texten. Analys: Klassen (S) läste."),)
    state = _state(*chunks)
    admit_batch(
        {
            "items": [
                _item(
                    ("body:0001",),
                    "2",
                    [[_text("Klassen läste inte texten. Analys:")]],
                    facit_text="Klassen (S) läste.",
                )
            ]
        },
        state,
    )
    item = _reviewed(state)
    assert "Klassen läste inte texten. Analys:" in body_plain_text(item.body)


def test_a_missing_instruction_beside_a_facit_remainder_goes_to_source_review_with_its_text():
    chunks = (
        _chunk(
            "body:0001",
            "2. Klassen läste inte texten. Markera subjekt och predikat. "
            "Analys: Klassen (S) läste (P).",
        ),
    )
    state = _state(*chunks)
    admit_batch(
        {
            "items": [
                _item(
                    ("body:0001",),
                    "2",
                    [[_text("Klassen läste inte texten.")], [_text("Analys:")]],
                    facit_text="Klassen (S) läste (P).",
                )
            ]
        },
        state,
    )
    item = _reviewed(state)
    assert "Klassen läste inte texten. Markera subjekt och predikat." in body_plain_text(item.body)


def test_a_remainder_that_is_only_a_blank_run_stays_out():
    chunks = (_chunk("body:0001", "2. Fyll i ____."),)
    item = _admit(chunks, _item(("body:0001",), "2", [[_text("Fyll i.")]]))
    assert body_plain_text(item.body) == "Fyll i."


def test_a_paragraph_with_an_inline_answer_label_is_unchanged():
    chunks = (_chunk("body:0001", "2. Vad är huvudstaden? Svar: Paris."),)
    state = _state(*chunks)
    admit_batch({"items": [_item(("body:0001",), "2", [[_text("Vad är huvudstaden?")]])]}, state)
    (aligned, _) = state.accepted[0]
    assert body_plain_text(aligned.item.body) == "Vad är huvudstaden?"


def test_a_remainder_that_a_choice_shows_is_unchanged():
    chunks = (_chunk("body:0001", "2. Ordet är Äpple."),)
    item = _admit(
        chunks,
        _item(
            ("body:0001",),
            "2",
            [[_text("Ordet är.")]],
            kind="single_choice",
            key_source="copied",
            facit_text="Äpple",
            choices=[_choice("Päron", False), _choice("Äpple", True)],
        ),
    )
    assert body_plain_text(item.body) == "Ordet är."
    assert [body_plain_text(choice.body) for choice in item.choices] == ["Päron", "Äpple"]


def test_two_exact_paragraphs_that_together_cover_the_source_are_unchanged():
    chunks = (_chunk("body:0001", "2. Alpha first. Beta second."),)
    item = _admit(
        chunks,
        _item(("body:0001",), "2", [[_text("Alpha first.")], [_text("Beta second.")]]),
    )
    assert body_plain_text(item.body) == "Alpha first.\nBeta second."


def test_a_reply_paragraph_with_a_gap_segment_is_unchanged():
    chunks = (_chunk("body:0001", "2. Fyll i ____."),)
    state = _state(*chunks)
    admit_batch(
        {
            "items": [
                {
                    **_item(("body:0001",), "2", [[_text("Fyll i "), _gap("ordet")]]),
                    "kind": "gap_fill",
                    "key_source": "invented",
                }
            ]
        },
        state,
    )
    (aligned, _) = state.accepted[0]
    assert body_plain_text(aligned.item.body) == "Fyll i [___]."


def test_a_short_first_cell_of_an_exact_joined_row_is_restored_whole():
    # REP-0049 review F2: the shortened cell's restore rebuilds the whole joined
    # row, so the already-kept second cell is not lost.
    left = "2. First sentence missing. Last sentence of first cell."
    right = "Second cell kept."
    chunks = (_table_chunk("body:0001", left, right),)
    item = _admit(
        chunks,
        _item(("body:0001",), "2", [[_text("Last sentence of first cell. | Second cell kept.")]]),
    )
    assert (
        body_plain_text(item.body)
        == "First sentence missing. Last sentence of first cell. | Second cell kept."
    )


def test_a_short_second_cell_of_an_exact_joined_row_is_restored_whole():
    left = "First cell kept."
    right = "Second cell kept start. Second cell missing end."
    chunks = (_table_chunk("body:0001", f"2. {left}", right),)
    item = _admit(
        chunks,
        _item(("body:0001",), "2", [[_text(f"{left} | Second cell kept start.")]]),
    )
    assert body_plain_text(item.body) == f"{left} | {right}"


def test_a_whole_exact_joined_row_is_unchanged():
    left = "2. First cell whole."
    right = "Second cell whole."
    chunks = (_table_chunk("body:0001", left, right),)
    item = _admit(
        chunks,
        _item(("body:0001",), "2", [[_text("First cell whole. | Second cell whole.")]]),
    )
    assert body_plain_text(item.body) == "First cell whole. | Second cell whole."


def test_a_shortened_opening_paragraph_restores_without_the_printed_number():
    chunks = (_chunk("body:0001", "1. Alpha first. Beta second."),)
    item = _admit(chunks, _item(("body:0001",), None, [[_text("Alpha first.")]]))
    assert body_plain_text(item.body) == "Alpha first. Beta second."


def test_a_whole_opening_paragraph_without_the_printed_number_is_unchanged():
    chunks = (_chunk("body:0001", "1. Alpha first."),)
    item = _admit(chunks, _item(("body:0001",), None, [[_text("Alpha first.")]]))
    assert body_plain_text(item.body) == "Alpha first."


def test_a_shortened_later_paragraph_keeps_its_own_number():
    chunks = (
        _chunk("body:0001", "1. Intro sentence."),
        _chunk("body:0002", "2) Part one. Part two."),
    )
    item = _admit(
        chunks,
        _item(
            ("body:0001", "body:0002"),
            None,
            [[_text("Intro sentence.")], [_text("Part one.")]],
        ),
    )
    assert body_plain_text(item.body) == "Intro sentence.\n2) Part one. Part two."
