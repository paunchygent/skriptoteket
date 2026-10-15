"""A question that conflicts twice is resent once, then kept as converted with the type mark.

The fresh english-exam recording holds q43's reply as a ``type_conflict`` that states a key
source over an incomplete key. Admission uses only a conflict's anchors and kind, so that raw
reply is served unchanged and still causes the resend. The one resend is synthesized in
memory (explicitly synthetic; the raw recordings are untouched). It reports the other kind
again, so the question is kept as converted with the kind the source shows, exactly one
resend, and the type-check mark. A kept reply is built like a converted one: a kept reply
whose key breaks the converted rules becomes the question's source review item.
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
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


def _recorded_conflict() -> dict[str, JsonValue]:
    return _item(recording(_EXAM, _RECORDED))


def _resend(*, gap_values: list[str]) -> dict[str, JsonValue]:
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
                        "asset_id": None,
                    },
                    {
                        "kind": "gap",
                        "text": None,
                        "accepted_values": list[JsonValue](gap_values),
                        "asset_id": None,
                    },
                    {
                        "kind": "text",
                        "text": " lunch menu.",
                        "accepted_values": [],
                        "asset_id": None,
                    },
                ]
            }
        ],
    )
    return content


class _ConflictedReplies(ReplayProvider):
    """Serve the fresh recordings unchanged and q43's one resend from memory."""

    def __init__(self, exam: str, *, gap_values: list[str]) -> None:
        super().__init__(exam)
        self.gap_values = gap_values

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        if request.item_id.endswith("c01"):
            self.requests.append(request)
            self.recording_ids[request.item_id] = f"synthetic_{_RECORDED}c01"
            return StructuredLLMResponse(
                content=_resend(gap_values=self.gap_values),
                finish_reason="completed",
                usage=StructuredLLMUsage(),
            )
        return await super().complete_structured(request=request, profile=profile)


async def _convert(gap_values: list[str] | None = None):
    provider = _ConflictedReplies(_EXAM, gap_values=["its"] if gap_values is None else gap_values)
    replay = build_replay(_EXAM, provider=provider)
    return replay, await replay.pipeline.convert(job=replay.job())


def test_the_recorded_conflict_states_a_key_source_over_an_incomplete_key():
    item = _recorded_conflict()

    assert item["outcome"] == "type_conflict"
    assert item["conflict_kind"] == _CONFLICT_KIND
    assert item["key_source"] is not None


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


async def test_a_kept_reply_whose_key_breaks_the_converted_rules_is_its_source_review():
    # A copied key source over a gap without accepted values is no converted item.
    _, outcome = await _convert(gap_values=[])

    document = outcome.update.document
    (item,) = [i for i in document.items if i.source_anchor == _CONFLICTED]
    assert item.review.reasons
    codes = [e.code for e in outcome.result.events]
    assert codes.count("type_conflict_kept") == 1
    assert "item_unparsed" in codes
