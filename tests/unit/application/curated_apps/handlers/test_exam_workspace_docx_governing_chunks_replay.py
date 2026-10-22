"""A governing chunk an item lists belongs to the section parent, not to the item (D40).

Both tests serve the fresh course-exam recording with the first wave reply rewritten in
memory (explicitly synthetic): the governing chunk body:0009 leaves the reply's instructions
and joins q1's item instead, the shape the historical recordings captured. When a body paragraph
is aligned to the chunk, assembly releases the chunk to the parent and removes that paragraph
from the item (TASK-SKRIPT-39-04-14). When the chunk is the item's whole body, removing it would
leave no body: the item keeps it, an event names the chunk, and the parent still shows it.
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
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from skriptoteket.domain.llm_door import AiDoorCaller
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_REPLY = "docx_w1-01"
_GOVERNING = "body:0009"
_OWN = "body:0010"


def _segments(item: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    body = item["body"]
    assert isinstance(body, list)
    (paragraph,) = body
    assert isinstance(paragraph, dict)
    segments = paragraph["segments"]
    assert isinstance(segments, list)
    return [s for s in segments if isinstance(s, dict)]


def _anchors(item: dict[str, JsonValue]) -> list[JsonValue]:
    value = item["source_anchors"]
    assert isinstance(value, list)
    return list(value)


def _without_instruction(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    instructions = content["instructions"]
    assert isinstance(instructions, list)
    content["instructions"] = [
        entry
        for entry in instructions
        if not (isinstance(entry, dict) and entry["source_anchors"] == [_GOVERNING])
    ]
    return content


def _listed_in_an_item(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    content = _without_instruction(content)
    items = content["items"]
    assert isinstance(items, list)
    item = items[0]
    assert isinstance(item, dict)
    item["source_anchors"] = [_GOVERNING, *_anchors(item)]
    (segment,) = _segments(item)
    segment["text"] = "Skriv rätt bokstav.\n" + str(segment["text"])
    return content


def _item_whole_body(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    content = _without_instruction(content)
    items = content["items"]
    assert isinstance(items, list)
    item = items[0]
    assert isinstance(item, dict)
    item["source_anchors"] = [_GOVERNING, *_anchors(item)]
    (segment,) = _segments(item)
    segment["text"] = "Skriv rätt bokstav."
    item["body"] = [{"segments": [segment]}]
    return content


class _RewrittenReplies(ReplayProvider):
    """Serve the fresh recordings with the first wave reply rewritten in memory."""

    def __init__(self, exam: str, rewrite) -> None:
        super().__init__(exam)
        self._rewrite = rewrite

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
        if self.recording_ids.get(request.item_id) != _REPLY:
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=self._rewrite(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_a_governing_chunk_an_item_prints_moves_to_the_parent():
    replay = build_replay(_EXAM, provider=_RewrittenReplies(_EXAM, _listed_in_an_item))
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    governed = [item_id for qid in ("q1", "q2", "q3") for item_id in outcome.update.item_ids[qid]]
    parent = document.parent_of(governed[0])
    assert parent is not None
    assert text[_GOVERNING] in body_text_lines(parent.instruction)
    first = next(i for i in document.items if i.item_id == governed[0])
    assert text[_GOVERNING] not in first.plain_text_lines()
    assert "governing_text_kept" not in {e.code for e in outcome.result.events}
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []


async def test_a_governing_chunk_that_is_an_item_whole_body_is_kept_and_reported():
    replay = build_replay(_EXAM, provider=_RewrittenReplies(_EXAM, _item_whole_body))
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    (kept,) = [i for i in document.items if i.source_anchor == _OWN]
    assert text[_GOVERNING] in kept.plain_text_lines(), "the wording vanished with no body left"
    kept_codes = [
        (e.code, e.anchors) for e in outcome.result.events if e.code == "governing_text_kept"
    ]
    assert kept_codes == [("governing_text_kept", (_GOVERNING,))]
    governed = [item_id for qid in ("q1", "q2", "q3") for item_id in outcome.update.item_ids[qid]]
    parent = document.parent_of(governed[0])
    assert parent is not None
    assert text[_GOVERNING] in body_text_lines(parent.instruction)
    assert text[_GOVERNING] not in body_text_lines(document.instructions)
