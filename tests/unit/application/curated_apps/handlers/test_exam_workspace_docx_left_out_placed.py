"""The left-out mark is decided on the placed item, by anchor (TASK-SKRIPT-39-04-19).

Admission records which own chunks an item leaves out and keeps the
``own_chunks_left_out`` event; the final built item carries the mark only for own
chunks still not shown. A listed heading that section placement restores leaves no
mark and no review reason; a genuinely missing chunk is still marked. The retry
path, which has no section placement, renders the mark on its replacement.
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
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    question_retry_source,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_left_out_test_support import (
    _STEM,
    _item,
    _state,
    _text,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    Env,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    document as make_document,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    item as make_item,
)

pytestmark = pytest.mark.unit

_WORD_BANK = "Använd orden: rim, meter, strof"
_POINTS_REASON = "Tryckta 1 poäng kan inte fördelas på frågans bedömning. Kontrollera poängen."


def _chunk(anchor: str, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, kind, text, text)


def _heading_state(*specs: tuple[str, str, str]) -> DocxBuildState:
    chunks = tuple(_chunk(anchor, kind, text) for anchor, kind, text in specs)
    return DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(chunk.anchor for chunk in chunks),),
    )


def _left_out_events(state: DocxBuildState) -> list[tuple[int | None, tuple[str, ...]]]:
    return [
        (event.item, event.anchors) for event in state.events if event.code == "own_chunks_left_out"
    ]


def test_a_listed_heading_that_placement_restores_leaves_no_mark():
    state = _heading_state(
        ("body:0001", "heading", "Del A"), ("body:0002", "paragraph", "1. Förklara.")
    )

    admit_batch(
        {"items": [_item(["body:0001", "body:0002"], body=[{"segments": [_text("Förklara.")]}])]},
        state,
    )

    (final,) = state.result().document.items
    assert body_plain_text(final.body).startswith("Del A")
    assert final.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert final.review.reasons == ()
    assert _left_out_events(state) == [(0, ("body:0001",))]


def test_a_genuinely_missing_listed_word_bank_is_still_marked_on_the_final_item():
    state = _state(_STEM, _WORD_BANK)

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    (final,) = state.result().document.items
    assert final.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert final.review.reasons == (LEFT_OUT_REASON, _WORD_BANK)
    assert _left_out_events(state) == [(0, ("body:0002",))]


def test_a_restored_heading_plus_a_missing_word_bank_marks_only_the_word_bank():
    state = _heading_state(
        ("body:0001", "heading", "Del A"),
        ("body:0002", "paragraph", "1. Förklara."),
        ("body:0003", "paragraph", _WORD_BANK),
    )

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    body=[{"segments": [_text("Förklara.")]}],
                )
            ]
        },
        state,
    )

    (final,) = state.result().document.items
    assert body_plain_text(final.body).startswith("Del A")
    assert final.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert final.review.reasons == (LEFT_OUT_REASON, _WORD_BANK)
    assert _left_out_events(state) == [(0, ("body:0001", "body:0003"))]


def test_a_restored_heading_keeps_an_unrelated_reason_without_the_left_out_mark():
    state = _heading_state(
        ("body:0001", "heading", "Del A"),
        ("body:0002", "paragraph", "1. Förklara. (1 p)"),
    )

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002"],
                    body=[{"segments": [_text("Förklara. (1 p)")]}],
                    points=2,
                    criteria=[
                        {"text": "Ett exempel.", "points": 1},
                        {"text": "En term.", "points": 1},
                    ],
                )
            ]
        },
        state,
    )

    (final,) = state.result().document.items
    assert body_plain_text(final.body).startswith("Del A")
    assert final.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert final.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert final.review.reasons == (_POINTS_REASON,)
    assert _left_out_events(state) == [(0, ("body:0001",))]


def _retry_reply(anchors: tuple[str, ...], *texts: str) -> dict[str, JsonValue]:
    return {
        "title": None,
        "instructions": [],
        "answer_key_anchors": [],
        "items": [
            {
                "source_anchors": list(anchors),
                "outcome": "converted",
                "conflict_kind": None,
                "review_reason": None,
                "kind": "free_text",
                "key_source": None,
                "facit_text": None,
                "printed_label": None,
                "body": [
                    {"segments": [{"kind": "text", "text": text, "accepted_values": []}]}
                    for text in texts
                ],
                "points": 1,
                "choices": [],
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "criteria": [],
            }
        ],
    }


@pytest.fixture()
def env() -> Env:
    return Env()


@pytest.mark.asyncio
async def test_retry_reply_leaving_an_own_chunk_out_marks_the_replacement(env: Env):
    stem, extra = "Beskriv försöket.", "Motivera slutsatsen."
    chunks = (
        _chunk("body:0001", "paragraph", stem),
        _chunk("body:0002", "paragraph", extra),
    )
    saved_source = question_retry_source(
        own_anchors=("body:0001", "body:0002"),
        owned_context_anchors=(),
        key_anchors=(),
        read_anchors=frozenset(),
        chunks=chunks,
        label_kind=NativeExamItemKind.FREE_TEXT,
    )
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", text=stem, source=saved_source),),
    )
    await env.seed(document)
    env.exchange.reply = _retry_reply(("body:0001", "body:0002"), extra)

    response = await env.retry(document)

    item = response.item
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons == (LEFT_OUT_REASON, stem)


@pytest.mark.asyncio
async def test_retry_reply_leaving_an_own_chunk_out_still_marks_it_when_it_joins_owned_context(
    env: Env,
):
    stem, owned, extra = "Beskriv försöket.", "Läs texten.", "Motivera slutsatsen."
    chunks = (
        _chunk("body:0001", "paragraph", stem),
        _chunk("body:0002", "paragraph", owned),
        _chunk("body:0003", "paragraph", extra),
    )
    saved_source = question_retry_source(
        own_anchors=("body:0001", "body:0003"),
        owned_context_anchors=("body:0002",),
        key_anchors=(),
        read_anchors=frozenset(),
        chunks=chunks,
        label_kind=NativeExamItemKind.FREE_TEXT,
    )
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", text=stem, source=saved_source),),
    )
    await env.seed(document)
    env.exchange.reply = _retry_reply(("body:0001", "body:0003"), extra)

    response = await env.retry(document)

    item = response.item
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.plain_text_lines() == (owned, extra)
    assert item.review.reasons == (LEFT_OUT_REASON, stem)
