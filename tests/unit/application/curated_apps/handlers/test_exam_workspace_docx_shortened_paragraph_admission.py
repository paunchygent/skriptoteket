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
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

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
    label: str,
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


def test_a_remainder_the_facit_shows_stays_out():
    chunks = (_chunk("body:0001", "2. Klassen läste inte texten. Analys: Klassen (S) läste."),)
    item = _admit(
        chunks,
        _item(
            ("body:0001",),
            "2",
            [[_text("Klassen läste inte texten. Analys:")]],
            facit_text="Klassen (S) läste.",
        ),
    )
    assert body_plain_text(item.body) == "Klassen läste inte texten. Analys:"
    assert item.facit_text == "Klassen (S) läste."


def test_a_missing_instruction_beside_a_facit_remainder_restores_only_the_instruction():
    chunks = (
        _chunk(
            "body:0001",
            "2. Klassen läste inte texten. Markera subjekt och predikat. "
            "Analys: Klassen (S) läste (P).",
        ),
    )
    item = _admit(
        chunks,
        _item(
            ("body:0001",),
            "2",
            [[_text("Klassen läste inte texten.")], [_text("Analys:")]],
            facit_text="Klassen (S) läste (P).",
        ),
    )
    assert "Klassen läste inte texten. Markera subjekt och predikat." in body_plain_text(item.body)
    assert "(S)" not in body_plain_text(item.body)
    assert item.facit_text == "Klassen (S) läste (P)."


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
