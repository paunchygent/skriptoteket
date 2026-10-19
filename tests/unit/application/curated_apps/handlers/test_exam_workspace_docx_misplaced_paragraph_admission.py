"""An item whose reply paragraph repeats another question's source shows its own stem instead
and carries no left-out mark; the other item is unchanged (TASK-SKRIPT-39-04-15 D4)."""

from base64 import b64decode
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
    DocxImage,
    DocxSourceParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import FORMATTING_REASON

pytestmark = pytest.mark.unit

_Q1 = "1. Which term names the pattern?"
_Q2 = "2. Read the stanza: We played all day."
_FOREIGN = "1. Explain the water cycle."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _table_chunk(anchor: str, *cells: str) -> DocxChunk:
    text = " | ".join(cells)
    paragraphs = []
    offset = 0
    for cell in cells:
        paragraphs.append(DocxSourceParagraph(offset, cell))
        offset += len(cell) + len(" | ")
    return DocxChunk(anchor, "table", text, text, paragraphs=tuple(paragraphs))


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _item(anchors: tuple[str, ...], label: str, *body_texts: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
        "body": [{"segments": [_text(text)]} for text in body_texts],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def test_an_item_repeating_another_questions_stem_shows_its_own_stem_without_a_left_out_mark():
    chunks = (_chunk("body:0001", _Q1), _chunk("body:0002", _Q2))
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002",)),
    )

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", _Q1[3:]),
                _item(("body:0002",), "2", _Q1[3:]),
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == _Q1[3:]
    assert body_plain_text(second.body) == _Q2[3:]
    assert second.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [event for event in state.events if event.code == "own_chunks_left_out"] == []

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == _Q1[3:]
    assert body_plain_text(second_final.body) == _Q2[3:]
    assert first_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.reasons == ()


def test_points_in_the_middle_of_a_stem_leaves_the_whole_stem_rebuilt():
    chunks = (
        _chunk("body:0001", _FOREIGN),
        _chunk("body:0002", "2. Describe (2 p) the rock cycle."),
        _chunk("body:0003", "Use a diagram."),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002", "body:0003")),
    )

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", _FOREIGN[3:]),
                _item(("body:0002", "body:0003"), "2", _FOREIGN[3:], "Use a diagram."),
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == _FOREIGN[3:]
    assert body_plain_text(second.body) == "Describe the rock cycle.\nUse a diagram."
    assert second.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [event for event in state.events if event.code == "own_chunks_left_out"] == []

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == _FOREIGN[3:]
    assert body_plain_text(second_final.body) == "Describe the rock cycle.\nUse a diagram."
    assert second_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.reasons == ()


def test_points_in_a_table_cell_leaves_the_whole_cell_rebuilt():
    chunks = (
        _chunk("body:0001", _FOREIGN),
        _table_chunk("body:0002", "2. Describe (2 p) the rock cycle.", "Use a diagram."),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002",)),
    )

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", _FOREIGN[3:]),
                _item(("body:0002",), "2", _FOREIGN[3:], "Use a diagram."),
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == _FOREIGN[3:]
    assert body_plain_text(second.body) == "Describe the rock cycle.\nUse a diagram."
    assert second.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [event for event in state.events if event.code == "own_chunks_left_out"] == []

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == _FOREIGN[3:]
    assert body_plain_text(second_final.body) == "Describe the rock cycle.\nUse a diagram."
    assert second_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.reasons == ()


def test_points_right_after_the_label_leaves_the_whole_stem_rebuilt():
    chunks = (
        _chunk("body:0001", _FOREIGN),
        _chunk("body:0002", "2. (2 p) Describe the rock cycle."),
        _chunk("body:0003", "Use a diagram."),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002", "body:0003")),
    )

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", _FOREIGN[3:]),
                _item(("body:0002", "body:0003"), "2", _FOREIGN[3:], "Use a diagram."),
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == _FOREIGN[3:]
    assert body_plain_text(second.body) == "Describe the rock cycle.\nUse a diagram."
    assert second.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [event for event in state.events if event.code == "own_chunks_left_out"] == []

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == _FOREIGN[3:]
    assert body_plain_text(second_final.body) == "Describe the rock cycle.\nUse a diagram."
    assert second_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.reasons == ()


_PIXEL_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
)


def test_an_unrenderable_own_picture_paragraph_goes_to_source_review():
    picture_text = "2. Explain the process in this diagram."
    image = DocxImage(
        payload=_PIXEL_PNG, media_type="image/png", offset=picture_text.index("process")
    )
    picture_chunk = DocxChunk("body:0002", "paragraph", picture_text, picture_text, images=(image,))
    chunks = (_chunk("body:0001", _FOREIGN), picture_chunk)
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002",)),
    )
    body: list[JsonValue] = [
        {"segments": [_text(_FOREIGN[3:])]},
        {
            "segments": [
                {
                    "kind": "asset",
                    "asset_id": image.asset_id,
                    "text": None,
                    "accepted_values": [],
                }
            ]
        },
    ]
    reply = _item(("body:0002",), "2", _FOREIGN[3:])
    reply["body"] = body

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", _FOREIGN[3:]),
                reply,
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == _FOREIGN[3:]
    assert first.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert second.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert second.review.reasons == (FORMATTING_REASON,)
    assert body_plain_text(second.body) == picture_text
    assert second.body_asset_ids() == (image.asset_id,)
    assert [event for event in state.events if event.code == "formatting_transfer_failed"] != []

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == _FOREIGN[3:]
    assert first_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert second_final.review.reasons == (FORMATTING_REASON,)
    assert body_plain_text(second_final.body) == picture_text


def test_an_unrenderable_inline_answer_key_paragraph_goes_to_source_review():
    own = "2. What is the capital? Svar: Paris."
    chunks = (_chunk("body:0001", _FOREIGN), _chunk("body:0002", own))
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002",)),
    )

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", _FOREIGN[3:]),
                _item(("body:0002",), "2", _FOREIGN[3:]),
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == _FOREIGN[3:]
    assert second.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert second.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert second.review.reasons == (FORMATTING_REASON,)
    assert body_plain_text(second.body) == own
    assert second.answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE
    assert second.gaps == ()
    assert [event for event in state.events if event.code == "formatting_transfer_failed"] != []

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == _FOREIGN[3:]
    assert first_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert second_final.review.reasons == (FORMATTING_REASON,)
    assert body_plain_text(second_final.body) == own


def test_a_consumed_shared_paragraph_is_not_rebuilt_from_the_next_own_paragraph():
    shared = "Give a reason."
    chunks = (
        _chunk("body:0001", shared),
        _chunk("body:0002", shared),
        _chunk("body:0003", "Describe the rock cycle."),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0001",), ("body:0002", "body:0003")),
    )

    admit_batch(
        {
            "items": [
                _item(("body:0001",), "1", shared),
                _item(("body:0002", "body:0003"), "2", shared, shared),
            ]
        },
        state,
    )

    first, second = (aligned.item for aligned, _ in state.accepted)
    assert body_plain_text(first.body) == shared
    assert body_plain_text(second.body) == "Give a reason.\nGive a reason."
    assert body_plain_text(second.body) != "Give a reason.\nDescribe the rock cycle."
    assert second.review.state is NativeItemReviewState.REVIEW_COMPLETE

    first_final, second_final = state.result().document.items
    assert body_plain_text(first_final.body) == shared
    assert body_plain_text(second_final.body) == "Give a reason.\nGive a reason."
    assert second_final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert second_final.review.reasons == ()
