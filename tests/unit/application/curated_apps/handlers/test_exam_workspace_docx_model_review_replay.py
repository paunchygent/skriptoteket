"""A review item holds the whole question, whether the model marked it or it failed to build.

The first test serves the fresh course-exam recording with q16's reply rewritten in memory
(explicitly synthetic): the item keeps its shape but its outcome becomes ``review``. The
review item shows every chunk of the question, facit included, between its neighbours, and
it blocks export. The second test rewrites q20's item into a gapless statement that lists
only part of its question; the native contract rejects it, and the review item still shows
every own chunk of the question plus every chunk the reply listed, in source order.
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
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
_REPLY = "docx_w1-02"
_QUESTION = "body:0061"
_QUESTION_OWN = ("body:0061", "body:0063")
_FAILED_QUESTION = "body:0085"
_FAILED_OWN = ("body:0085", "body:0086")
_FAILED_LISTED = "body:0087"
_REASON = "Otydlig uppgift."


def _anchors(entry: dict[str, JsonValue]) -> list[JsonValue]:
    value = entry["source_anchors"]
    assert isinstance(value, list)
    return list(value)


def _item(content: dict[str, JsonValue], anchor: str) -> dict[str, JsonValue]:
    items = content["items"]
    assert isinstance(items, list)
    (item,) = [entry for entry in items if isinstance(entry, dict) and anchor in _anchors(entry)]
    return item


def _marked_for_review(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    item = _item(content, _QUESTION)
    item["outcome"] = "review"
    item["review_reason"] = _REASON
    return content


def _failed_item(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    item = _item(content, _FAILED_QUESTION)
    item["key_source"] = None
    item["source_anchors"] = [_FAILED_QUESTION, _FAILED_LISTED]
    item["body"] = [
        {
            "segments": [
                {
                    "kind": "text",
                    "text": "De väntar inte. är en huvudsats.",
                    "accepted_values": [],
                    "asset_id": None,
                }
            ]
        }
    ]
    return content


class _RewrittenReplies(ReplayProvider):
    """Serve the fresh recordings with one reply rewritten in memory for one scenario."""

    def __init__(self, exam: str, rewrite) -> None:
        super().__init__(exam)
        self._rewrite = rewrite

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(request=request, profile=profile)
        if self.recording_ids.get(request.item_id) != _REPLY:
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=self._rewrite(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_a_model_review_item_shows_every_source_chunk_of_its_question_in_order():
    replay = build_replay(_EXAM, provider=_RewrittenReplies(_EXAM, _marked_for_review))
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    (item,) = [i for i in document.items if i.source_anchor == _QUESTION]
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.review.reasons == (f"AI-tolkningen markerade frågan för granskning: {_REASON}",)
    printed = "\n".join(item.plain_text_lines())
    own_positions = [printed.index(text[anchor]) for anchor in _QUESTION_OWN]
    assert own_positions == sorted(own_positions), "the question's chunks left source order"
    for anchor in _QUESTION_OWN:
        assert text[anchor] in printed
    for other in document.items:
        if other.sequence not in {item.sequence - 1, item.sequence + 1}:
            continue
        assert not other.review.reasons, "the fault spread to a neighbouring question"
    assert ("unbuilt_question", item.item_id) in {
        (blocker.reason, blocker.item_id) for blocker in native_export_blockers(document)
    }
    events = [e for e in outcome.result.events if e.code == "model_review"]
    assert [e.anchors for e in events] == [
        (  # one event, naming the admitted anchors
            _QUESTION,
            "body:0062",
            _QUESTION_OWN[1],
            "body:0064",
        )
    ]
    assert outcome.update.pending == ()


async def test_a_failed_item_listing_part_of_its_question_becomes_a_review_item_of_the_whole():
    replay = build_replay(_EXAM, provider=_RewrittenReplies(_EXAM, _failed_item))
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    (item,) = [i for i in document.items if i.source_anchor == _FAILED_QUESTION]
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    printed = "\n".join(item.plain_text_lines())
    for anchor in (*_FAILED_OWN, _FAILED_LISTED):
        assert text[anchor] in printed, f"{anchor} is missing from the review item"
    assert all(
        other.source_anchor not in {_FAILED_OWN[1], _FAILED_LISTED}
        for other in document.items
        if other.item_id != item.item_id
    )
