"""A gap_fill reply that places no gap is a review item naming the invariant (D32, D4).

The reply the test serves is the fresh course-exam recording with q16's item rewritten in
memory (explicitly synthetic): its gap segments become the text they interrupt, so the
schema-valid item declares kind ``gap_fill`` and half a key state but places no gap. The
native contract rejects it; the question becomes one review item holding its source text,
and the batch's other questions still convert.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = "body:0061"
_STEM = "body:0063"
_INVARIANT = "gap_fill items need at least one gap"


def _anchors(entry: dict[str, JsonValue]) -> list[JsonValue]:
    value = entry["source_anchors"]
    assert isinstance(value, list)
    return list(value)


def _texts(item: dict[str, JsonValue]) -> list[JsonValue]:
    body = item["body"]
    assert isinstance(body, list)
    segments: list[JsonValue] = []
    for paragraph in body:
        assert isinstance(paragraph, dict)
        raw_segments = paragraph["segments"]
        assert isinstance(raw_segments, list)
        for segment in raw_segments:
            assert isinstance(segment, dict)
            if segment["kind"] == "text":
                segments.append(
                    {
                        "kind": "text",
                        "text": segment["text"],
                        "accepted_values": [],
                        "asset_id": None,
                    }
                )
    return segments


def _drop_gaps(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The current raw reply with q16's gap segments replaced by their source text."""
    items = content["items"]
    assert isinstance(items, list)
    (item,) = [entry for entry in items if isinstance(entry, dict) and _QUESTION in _anchors(entry)]
    item["body"] = [{"segments": _texts(item)}]
    item["key_source"] = None
    return content


class _GaplessReplies(ReplayProvider):
    """Serve the fresh recordings with q16's reply rewritten to drop its gaps in memory."""

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(request=request, profile=profile)
        if self.recording_ids.get(request.item_id) != "docx_w1-02":
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=_drop_gaps(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_a_gap_fill_reply_without_a_gap_is_a_review_item_naming_the_invariant():
    replay = build_replay(_EXAM, provider=_GaplessReplies(_EXAM))
    outcome = await replay.pipeline.convert(job=replay.job())

    events = [
        event
        for event in outcome.result.events
        if event.code == "native_contract_invalid" and _QUESTION in event.anchors
    ]
    assert len(events) == 1
    assert _INVARIANT in events[0].detail
    item = next(i for i in outcome.result.document.items if i.source_anchor == _QUESTION)
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert any(_INVARIANT in reason for reason in item.review.reasons)
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    assert any(text[_STEM] in line for line in item.plain_text_lines()), (
        "the review item lost its source text"
    )
    assert outcome.update.pending == ()
    (kept_id,) = outcome.update.item_ids["q1"]
    (kept,) = [i for i in outcome.result.document.items if i.item_id == kept_id]
    assert not kept.review.reasons, "the fault spread outside its question"
