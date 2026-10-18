"""An item whose reply paragraph repeats another question's source shows its own stem instead
and carries no left-out mark; the other item is unchanged (TASK-SKRIPT-39-04-15 D4)."""

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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit

_Q1 = "1. Which term names the pattern?"
_Q2 = "2. Read the stanza: We played all day."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _item(anchors: tuple[str, ...], label: str, body_text: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
        "body": [{"segments": [_text(body_text)]}],
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
