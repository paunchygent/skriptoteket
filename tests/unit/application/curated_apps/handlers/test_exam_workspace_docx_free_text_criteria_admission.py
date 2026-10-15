"""A Fritext criteria reply the native contract cannot hold keeps its source as review (Q12, R14).

Admission never rejects the batch: a question whose criteria cannot become the native
criteria list becomes one review item holding that question's own source text, and the
batch's other questions still convert.
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind="paragraph", text=text, marked_text=text)


def _state(question_text: str) -> DocxBuildState:
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=(
            _chunk("body:0001", question_text),
            _chunk("body:0002", "Bedöm helheten."),
        ),
    )


def _content(points: JsonValue, criteria: list[JsonValue]) -> dict[str, JsonValue]:
    return {
        "title": None,
        "instructions": [],
        "answer_key_anchors": ["body:0002"],
        "items": [
            {
                "source_anchors": ["body:0001"],
                "outcome": "converted",
                "conflict_kind": None,
                "review_reason": None,
                "kind": "free_text",
                "printed_label": None,
                "key_source": None,
                "facit_text": "Bedöm helheten.",
                "body": [
                    {
                        "segments": [
                            {
                                "kind": "text",
                                "text": "Resonera.",
                                "accepted_values": [],
                                "spelling_candidates": [],
                                "asset_id": None,
                            }
                        ]
                    }
                ],
                "points": points,
                "choices": [],
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "criteria": criteria,
            }
        ],
    }


def _assert_source_review_without_failing_the_batch(state: DocxBuildState) -> None:
    (entry,) = state.accepted
    item, anchors = entry
    assert anchors == ("body:0001",)
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.criteria == ()
    assert any("Resonera." in line for line in item.plain_text_lines())
    (event,) = [event for event in state.events if event.code == "item_unbuildable"]
    assert event.anchors == ("body:0001",)
    assert event.detail == "ValueError"


def test_a_fractional_printed_point_becomes_the_questions_review_item() -> None:
    state = _state("Resonera. (2,5 p)")

    admit_batch(
        _content(None, [{"text": "Bedöm helheten.", "points": None}]),
        state,
    )

    _assert_source_review_without_failing_the_batch(state)


def test_a_criteria_sum_that_differs_from_the_printed_points_becomes_a_review_item() -> None:
    state = _state("Resonera. (4 p)")

    admit_batch(
        _content(
            4,
            [
                {"text": "Ett exempel.", "points": 2},
                {"text": "En term.", "points": 1},
            ],
        ),
        state,
    )

    _assert_source_review_without_failing_the_batch(state)
