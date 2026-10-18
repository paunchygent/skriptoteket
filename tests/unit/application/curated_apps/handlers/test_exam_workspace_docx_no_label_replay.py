"""A question neither labeling pass labels becomes a review item the teacher labels (D23).

The fresh course-exam recording escalates q21 to the second pass. This test serves the same
run with two explicitly synthetic in-memory changes: the Decisions first pass refuses q21
(no probabilities, so it has no top label) and the second pass answers unresolved. No
converter request holds the question; it becomes one review item holding its own chunks as
printed, at its place, and the labeling event names it.
"""

from __future__ import annotations

import copy
import json

import httpx
import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    UNLABELED_REASON,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers import docx_pipeline_replay
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = "q21"
# q21's own chunks; "Poäng: 1 poäng" (body:0096) is its own points line (TASK-SKRIPT-39-04-11 D2).
_OWN = ("body:0093", "body:0094", "body:0096")


def _refusing_decisions(exam: str, root=None) -> httpx.AsyncClient:
    """Serve the current decisions payload with q21's answer rewritten to a refusal."""
    payload = copy.deepcopy(docx_pipeline_replay.recording(exam, "decisions_1"))
    answers = payload["answers"]
    assert isinstance(answers, list)
    (answer,) = [
        entry for entry in answers if isinstance(entry, dict) and entry["name"] == "kind_q21"
    ]
    answer.clear()
    answer.update({"type": "refusal", "name": "kind_q21"})

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and request.url.path.endswith("/decisions")
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handle))


class _UnresolvedLabel(ReplayProvider):
    """Serve the fresh recordings with q21's second-pass label rewritten to unresolved."""

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(request=request, profile=profile)
        if request.item_id != "label_b:q21":
            return response
        return StructuredLLMResponse(
            content={"label": "unresolved"},
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_a_question_neither_pass_labels_becomes_a_source_review_item(monkeypatch):
    monkeypatch.setattr(docx_pipeline_replay, "decisions_client", _refusing_decisions)
    provider = _UnresolvedLabel(_EXAM)
    replay = build_replay(_EXAM, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    for request in provider.requests:
        if not request.item_id.startswith("docx_w"):
            continue
        payload = json.loads(request.user_payload)
        claimed = {chunk["anchor"] for chunk in payload["chunks"]}
        assert not set(_OWN) & claimed, "a converter request holds the unlabeled question"
    texts = {c.anchor: c.text for c in corpus_chunks(_EXAM)}
    (item,) = [i for i in outcome.result.document.items if i.source_anchor == _OWN[0]]
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.review.reasons == (UNLABELED_REASON,)
    shown = [s.text for p in item.body for s in p.segments if isinstance(s, NativeTextSegment)]
    assert shown == [texts[anchor] for anchor in _OWN]
    assert item.item_id in outcome.update.item_ids[_QUESTION]
    events = [(e.code, e.anchors) for e in outcome.result.events if e.code == "question_unlabeled"]
    assert events and events[0][1] == tuple(_OWN)
    assert outcome.update.pending == ()
