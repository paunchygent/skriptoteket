"""A governing chunk no reply claims becomes its section parent's instruction (D40).

The fresh english-exam recording holds body:0058 as the instruction of the section that
governs q25-q27. This test serves the same recording with that instruction removed in memory
(explicitly synthetic): the chunk is then unclaimed, the fallback names it, and assembly
makes it its section parent's instruction of its source text. No item holds it and the
grouping still decides the parent's questions.
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
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_UNCLAIMED = "body:0058"


def _drops_the_instruction(content: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    instructions = content.get("instructions")
    if not isinstance(instructions, list):
        return None
    kept = [
        entry
        for entry in instructions
        if not (isinstance(entry, dict) and entry["source_anchors"] == [_UNCLAIMED])
    ]
    if len(kept) == len(instructions):
        return None
    content["instructions"] = kept
    return content


class _UnclaimedGoverning(ReplayProvider):
    """Serve the fresh recordings with body:0058's instruction removed from its reply."""

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
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        rewritten = _drops_the_instruction(content)
        if rewritten is None:
            return response
        return StructuredLLMResponse(
            content=rewritten, finish_reason=response.finish_reason, usage=response.usage
        )


async def test_an_unclaimed_governing_chunk_is_its_section_parent_s_instruction():
    contexts = recording(_EXAM, "docx_grouping_1")["shared_contexts"]
    assert isinstance(contexts, list)
    (context,) = [c for c in contexts if isinstance(c, dict) and c["anchor"] == _UNCLAIMED]
    governs = context["governs"]
    assert isinstance(governs, list) and len(governs) == 3

    replay = build_replay(_EXAM, provider=_UnclaimedGoverning(_EXAM))
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    governed = [item_id for qid in governs for item_id in outcome.update.item_ids[str(qid)]]
    parent = document.parent_of(governed[0])
    assert parent is not None
    assert text[_UNCLAIMED] in body_text_lines(parent.instruction)
    assert list(parent.item_ids) == governed
    assert all(item.source_anchor != _UNCLAIMED for item in document.items)
    assert text[_UNCLAIMED] not in body_text_lines(document.instructions)
    recorded = [(e.code, e.anchors) for e in outcome.result.events if _UNCLAIMED in e.anchors]
    assert ("governing_instruction", (_UNCLAIMED,)) in recorded
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []
