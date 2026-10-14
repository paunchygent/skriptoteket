"""A question that conflicts twice is resent once, then kept as converted with the type mark.

The fresh english-exam recording holds q43's reply as a ``type_conflict`` whose key is
incomplete, so the plain replay refuses it at the provenance validator. This test serves
the same raw reply from memory with its key state made consistent, and synthesizes the one
resend in memory from it (explicitly synthetic; the raw recordings are untouched). The
resend reports the other kind again, so the question is kept as converted with the kind the
source shows, exactly one resend, and the type-check mark.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_RECORDED = "docx_w2-11-01"
_CONFLICTED = "body:0115"
_CONFLICT_KIND = "single_choice"
_KEPT_KIND = NativeExamItemKind.GAP_FILL


def _item(content: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    items = content["items"]
    assert isinstance(items, list)
    (item,) = [entry for entry in items if isinstance(entry, dict)]
    return item


def _first_conflict(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The current raw conflict reply with an empty objective key's source left unstated."""
    item = _item(content)
    assert item["outcome"] == "type_conflict"
    assert item["conflict_kind"] == _CONFLICT_KIND
    item["key_source"] = None
    return content


def _resend() -> dict[str, JsonValue]:
    """The one synthesized resend: the current raw reply stating the other kind again."""
    content = copy.deepcopy(recording(_EXAM, _RECORDED))
    item = _item(content)
    item.update(
        outcome="type_conflict",
        conflict_kind=_KEPT_KIND.value,
        kind="single_choice",
        key_source="copied",
        facit_text="Correct answer: its",
        points=1,
        body=[
            {
                "segments": [
                    {
                        "kind": "text",
                        "text": "Write its or it’s. The school changed ",
                        "accepted_values": [],
                        "spelling_candidates": [],
                        "asset_id": None,
                    },
                    {
                        "kind": "gap",
                        "text": None,
                        "accepted_values": ["its"],
                        "spelling_candidates": [],
                        "asset_id": None,
                    },
                    {
                        "kind": "text",
                        "text": " lunch menu.",
                        "accepted_values": [],
                        "spelling_candidates": [],
                        "asset_id": None,
                    },
                ]
            }
        ],
    )
    return content


class _ConflictedReplies(ReplayProvider):
    """Serve the fresh recordings with q43's reply and its one resend rewritten in memory."""

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        if request.item_id.endswith("c01"):
            self.requests.append(request)
            self.recording_ids[request.item_id] = f"synthetic_{_RECORDED}c01"
            return StructuredLLMResponse(
                content=_resend(), finish_reason="completed", usage=StructuredLLMUsage()
            )
        response = await super().complete_structured(request=request, profile=profile)
        if self.recording_ids.get(request.item_id) != _RECORDED:
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=_first_conflict(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def _convert():
    replay = build_replay(_EXAM, provider=_ConflictedReplies(_EXAM))
    return replay, await replay.pipeline.convert(job=replay.job())


async def test_a_second_type_conflict_is_not_resent_again():
    replay, outcome = await _convert()

    resends = [item_id for item_id in replay.provider.request_ids if item_id.endswith("c01")]
    assert len(resends) == 1
    assert not [item_id for item_id in replay.provider.request_ids if item_id.endswith("c01c01")]
    assert outcome.update.pending == ()


async def test_the_twice_conflicted_family_is_kept_as_converted_with_the_type_mark():
    _, outcome = await _convert()

    document = outcome.update.document
    (item,) = [i for i in document.items if i.source_anchor == _CONFLICTED]
    assert item.kind is _KEPT_KIND
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert not item.review.reasons
    assert item.review.confidence is not None and item.review.confidence < 0.95
    assert item.gaps and item.gaps[0].accepted_values == ("its",)
    codes = [e.code for e in outcome.result.events]
    assert codes.count("type_conflict") == 1, "only the first reply may report a conflict"
    assert codes.count("type_conflict_kept") == 1


async def test_every_grouped_question_still_maps_to_items_with_no_shared_anchor():
    _, outcome = await _convert()
    update = outcome.update
    document = update.document

    assert update.pending == ()
    assert all(update.item_ids[qid] for qid in update.item_ids), "a question lost all its items"
    mapped = [item_id for ids in update.item_ids.values() for item_id in ids]
    mapped += update.extra_item_ids
    assert sorted(mapped) == sorted(item.item_id for item in document.items)
    anchors = [item.source_anchor for item in document.items]
    assert len(set(anchors)) == len(anchors), "a chunk anchor starts two items"
    position = {c.anchor: n for n, c in enumerate(corpus_chunks(_EXAM))}
    assert [position[a or ""] for a in anchors] == sorted(position[a or ""] for a in anchors)
