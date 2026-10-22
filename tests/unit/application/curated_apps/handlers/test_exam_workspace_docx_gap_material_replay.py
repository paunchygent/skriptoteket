"""A gap_fill reply that makes the material its line talks about a gap comes back as review.

D43, user decision 2026-10-12. The material detector reads the chunks the item claims; it
must fire for a reply that turns a phrase the source sets apart and its line talks about
into a gap, and must not fire for any gap_fill item of the fresh recordings. The first
test serves the fresh course-exam recording with q20's reply rewritten in memory
(explicitly synthetic): one existing gap's accepted value becomes the phrase "De väntar
inte." that body:0086 sets apart. The second test admits every converted gap_fill item the
fresh recordings hold and asserts no false positive.
"""

from __future__ import annotations

import copy
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_gap_material import (
    GAPPED_MATERIAL_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    ReplayProvider,
    build_replay,
    corpus_chunks,
    recorded_exams,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = "body:0085"
_MATERIAL = "De väntar inte."


def _anchors(entry: dict[str, JsonValue]) -> list[JsonValue]:
    value = entry["source_anchors"]
    assert isinstance(value, list)
    return list(value)


def _make_material_a_gap(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The current raw reply with q20's first gap accepting the material phrase."""
    items = content["items"]
    assert isinstance(items, list)
    (item,) = [entry for entry in items if isinstance(entry, dict) and _QUESTION in _anchors(entry)]
    body = item["body"]
    assert isinstance(body, list)
    for paragraph in body:
        assert isinstance(paragraph, dict)
        raw_segments = paragraph["segments"]
        assert isinstance(raw_segments, list)
        for segment in raw_segments:
            assert isinstance(segment, dict)
            if segment["kind"] == "gap":
                segment["accepted_values"] = [_MATERIAL]
                return content
    raise AssertionError("the recorded q20 item places no gap")


class _GappedMaterialReplies(ReplayProvider):
    """Serve the fresh recordings with q20's reply rewritten to make body:0086's material a gap."""

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(
            request=request, profile=profile, caller=caller
        )
        if self.recording_ids.get(request.item_id) != "docx_w1-02":
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=_make_material_a_gap(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_a_reply_that_makes_the_material_a_gap_comes_back_as_review_required():
    replay = build_replay(_EXAM, provider=_GappedMaterialReplies(_EXAM))
    outcome = await replay.pipeline.convert(job=replay.job())

    (event,) = [e for e in outcome.result.events if e.code == "gapped_material"]
    assert _QUESTION in event.anchors
    assert _MATERIAL in event.detail
    item = next(i for i in outcome.result.document.items if i.source_anchor == _QUESTION)
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert any(
        reason.startswith(GAPPED_MATERIAL_REASON) and _MATERIAL in reason
        for reason in item.review.reasons
    )
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    assert text["body:0086"] in "\n".join(item.plain_text_lines())
    (kept_id,) = outcome.update.item_ids["q1"]
    (kept,) = [i for i in outcome.result.document.items if i.item_id == kept_id]
    assert not kept.review.reasons, "the fault spread outside its question"
    assert outcome.update.pending == ()


def _gap_fill_items() -> list[tuple[str, str, int, dict[str, JsonValue]]]:
    entries: list[tuple[str, str, int, dict[str, JsonValue]]] = []
    for exam in recorded_exams():
        for path in sorted((RECORDINGS / exam).glob("docx_w*.json")):
            reply = recording(exam, path.stem)
            items = reply.get("items", [])
            assert isinstance(items, list)
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                if item.get("kind") == "gap_fill" and item.get("outcome") == "converted":
                    entries.append((exam, path.stem, index, item))
    return entries


async def test_no_fresh_recorded_gap_fill_item_is_sent_to_review_for_gapped_material():
    violations: list[str] = []
    for exam, name, index, item in _gap_fill_items():
        anchors = item["source_anchors"]
        assert isinstance(anchors, list)
        question = tuple(str(anchor) for anchor in anchors)
        state = DocxBuildState(
            origin_kind="docx_import",
            job_id=uuid4(),
            document_id=uuid4(),
            filename=f"{exam}.docx",
            source_sha256="0" * 64,
            chunks=corpus_chunks(exam),
            claimable=frozenset(question),
            questions=(question,),
        )
        admit_batch({"items": [item]}, state)
        if "gapped_material" in {e.code for e in state.events}:
            violations.append(f"{exam}/{name}[{index}] {question}")
    assert not violations, "false gapped_material positives: " + ", ".join(violations)
