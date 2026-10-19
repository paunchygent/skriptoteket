"""A gap_fill reply whose gap count differs from its source paragraph's blank runs goes to
review with ``gap_count_mismatch`` and never through the whole-body rebuild (D5,
TASK-SKRIPT-39-04-16). A reply that drops the cue beside a gap but keeps the gap count is
admitted with the source paragraph's cue restored in its body (D2, D4)."""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_TWO_BLANKS = "1. The bands ____ (spelar) ____ at the festival."
_ONE_BLANK = "1. The bands ____ (spelar) at the festival."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _state(*texts: str) -> DocxBuildState:
    chunks = tuple(_chunk(f"body:{n:04d}", text) for n, text in enumerate(texts, start=1))
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(c.anchor for c in chunks),),
    )


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _gap(*values: str) -> dict[str, JsonValue]:
    return {"kind": "gap", "text": None, "accepted_values": list(values)}


def _item(anchors: list[str], **fields: JsonValue) -> dict[str, JsonValue]:
    item: dict[str, JsonValue] = {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "gap_fill",
        "key_source": "invented",
        "facit_text": None,
        "printed_label": "1",
        "body": [{"segments": [_text("The bands "), _gap("play"), _text(" at the festival.")]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }
    item.update(fields)
    return item


def _texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def test_one_gap_for_a_two_blank_source_paragraph_goes_to_review_with_the_mismatch_detail():
    state = _state(_TWO_BLANKS)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001"],
                    body=[
                        {
                            "segments": [
                                _text("The bands "),
                                _gap("play"),
                                _text(" (spelar) ____ at the festival."),
                            ]
                        }
                    ],
                )
            ]
        },
        state,
    )

    events = [event for event in state.events if event.stage != "formatting"]
    assert [(event.code, event.detail) for event in events] == [
        ("gap_count_mismatch", "1 gaps for 2 blank runs")
    ]
    assert all(
        event.code not in {"item_unbuildable", "formatting_transfer_failed"}
        for event in state.events
    )
    ((admitted, anchors),) = [(accepted.item, held) for accepted, held in state.accepted]
    assert anchors == ("body:0001",)
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert _TWO_BLANKS[3:] in " ".join(_texts(admitted)), "the review item lost its source text"
    assert admitted.review.reasons == (
        "Frågan följer inte provformatet: 1 lucka men 2 svarsplatser.",
    )


def test_a_reply_that_drops_the_cue_but_keeps_the_gap_count_is_admitted_with_the_cue_back():
    state = _state(_ONE_BLANK)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001"],
                    body=[
                        {
                            "segments": [
                                _text("The bands "),
                                _gap("play"),
                                _text(" at the festival."),
                            ]
                        }
                    ],
                )
            ]
        },
        state,
    )

    assert [event for event in state.events if event.code == "gap_count_mismatch"] == []
    ((admitted, anchors),) = [(accepted.item, held) for accepted, held in state.accepted]
    assert anchors == ("body:0001",)
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert admitted.review.reasons == ()
    assert "(spelar)" in " ".join(_texts(admitted)), "the dropped cue was not restored"


def test_an_underscore_mismatch_with_an_inline_answer_key_goes_to_review_without_the_key():
    source = "1. The bands ____ (spelar) at the festival. Svar: play"
    state = _state(source)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001"],
                    body=[
                        {
                            "segments": [
                                _text("The bands "),
                                _gap("play"),
                                _gap("play"),
                                _text(" at the festival."),
                            ]
                        }
                    ],
                )
            ]
        },
        state,
    )

    events = [event for event in state.events if event.stage != "formatting"]
    assert [(event.code, event.detail) for event in events] == [
        ("gap_count_mismatch", "2 gaps for 1 blank runs")
    ]
    ((admitted, anchors),) = [(accepted.item, held) for accepted, held in state.accepted]
    assert anchors == ("body:0001",)
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert admitted.review.reasons == (
        "Frågan följer inte provformatet: 2 luckor men 1 svarsplats.",
    )
    text = " ".join(_texts(admitted))
    assert "The bands" in text
    assert "Svar:" not in text
