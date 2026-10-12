"""A question's own chunk that a reply lists only as an answer key, while an item lists another
chunk of the question, is left out of that item: the item's check mark shows it as printed and
it is no teacher note (D41)."""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    LEFT_OUT_REASON,
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_STEM = "1. Beskriv kort hur en intervju planeras."
_FACIT = "Svar: syfte, urval och frågor bestäms i förväg."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def test_an_own_chunk_listed_only_as_an_answer_key_joins_the_item_s_check_mark():
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=(_chunk("body:0001", _STEM), _chunk("body:0002", _FACIT)),
        questions=(("body:0001", "body:0002"),),
    )
    item: dict[str, JsonValue] = {
        "source_anchors": ["body:0001"],
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "title": _STEM,
        "printed_label": "1",
        "body": [{"segments": [{"kind": "text", "text": _STEM[3:], "accepted_values": []}]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "marking_guide": "",
    }

    admit_batch({"answer_key_anchors": ["body:0002"], "items": [item]}, state)

    assert state.key_anchors == set()
    ((admitted, anchors),) = state.accepted
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, _FACIT)
    assert [e.code for e in state.events] == ["own_chunks_left_out"]
    assert state.pending == ()
