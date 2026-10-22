"""A question keeps its own chunks whatever the reply lists (D41, D42, admission contract).

Both tests serve the fresh course-exam recording with q16's reply rewritten in memory
(explicitly synthetic). Listing the question's own chunk as an answer key does not move it
to a teacher note while the item holds it. An item that leaves out one of its question's
own chunks whose wording it still copies holds the chunk, and the item needs no check mark
because nothing is missing from it.
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
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.exam_answer_key import StructuredLLMTextObserver
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_REPLY = "docx_w1-02"
_QUESTION = "body:0061"
_OWN = "body:0063"


def _anchors(entry: dict[str, JsonValue]) -> list[JsonValue]:
    value = entry["source_anchors"]
    assert isinstance(value, list)
    return list(value)


def _item(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    items = content["items"]
    assert isinstance(items, list)
    (item,) = [entry for entry in items if isinstance(entry, dict) and _QUESTION in _anchors(entry)]
    return item


def _listed_as_answer_key(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The current raw reply listing q16's own chunk as one of its answer keys."""
    content["answer_key_anchors"] = [_OWN]
    return content


def _leaves_out_an_own_chunk(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The current raw reply silently leaving out one own chunk its wording still copies."""
    item = _item(content)
    anchors = item["source_anchors"]
    assert isinstance(anchors, list)
    item["source_anchors"] = [anchor for anchor in anchors if anchor != _OWN]
    return content


class _RewrittenReplies(ReplayProvider):
    """Serve the fresh recordings with q16's reply rewritten in memory for one scenario."""

    def __init__(self, exam: str, rewrite) -> None:
        super().__init__(exam)
        self._rewrite = rewrite

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(
            request=request, profile=profile, caller=caller, on_text=on_text
        )
        if self.recording_ids.get(request.item_id) != _REPLY:
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=self._rewrite(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_a_question_own_chunk_listed_as_an_answer_key_stays_with_its_item():
    replay = build_replay(_EXAM, provider=_RewrittenReplies(_EXAM, _listed_as_answer_key))
    outcome = await replay.pipeline.convert(job=replay.job())

    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    (item,) = [i for i in outcome.result.document.items if i.source_anchor == _QUESTION]
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert any("I ordet lekfullheten" in line for line in item.plain_text_lines())
    assert text[_OWN] not in outcome.result.notes


async def test_an_item_that_leaves_out_an_own_chunk_it_still_copies_needs_no_check_mark():
    replay = build_replay(_EXAM, provider=_RewrittenReplies(_EXAM, _leaves_out_an_own_chunk))
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    (item,) = [i for i in document.items if i.source_anchor == _QUESTION]
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()
    assert any("I ordet lekfullheten" in line for line in item.plain_text_lines())
    assert all(other.source_anchor != _OWN for other in document.items)
    assert "own_chunks_left_out" not in {e.code for e in outcome.result.events}
    assert all(blocker.item_id != item.item_id for blocker in native_export_blockers(document))
    assert outcome.update.pending == ()
