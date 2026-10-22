"""A question's own chunk listed as an instruction stands only at its question (D42).

The fresh poetry-exam recording lists q5's lead-in body:0018 as an instruction while q5's
item does not list it, and the lead-in stands on the parent that holds q5 and q6. The second
test serves the fresh grammar-exam recording with q2's reply rewritten in memory (explicitly
synthetic): its own line body:0017 leaves the item's anchors and becomes an instruction, and
placement keeps it at its question, between the printed heading and the first part.
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
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
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

_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_GRAMMAR = "svenska_2_grammatik_omprov_variant_1_med_facit"
_GRAPH_REPLY = "docx_w2-03-01"
_GRAMMAR_QUESTION = "q2"
_GRAMMAR_LINE = "body:0017"


async def test_an_own_lead_in_a_reply_lists_as_an_instruction_stands_on_the_parent_it_opens():
    questions = recording(_POETRY, "docx_grouping_1")["questions"]
    assert isinstance(questions, list)
    (question,) = [q for q in questions if isinstance(q, dict) and q["id"] == "q5"]
    assert question["anchors"] == ["body:0018", "body:0019", "body:0020"]
    reply = recording(_POETRY, "docx_w1-01")
    instructions = reply["instructions"]
    assert isinstance(instructions, list)
    assert any(isinstance(i, dict) and i["source_anchors"] == ["body:0018"] for i in instructions)

    replay = build_replay(_POETRY)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    lead_in = {c.anchor: c.text for c in corpus_chunks(_POETRY)}["body:0018"]
    assert lead_in == "Read the sentence:"
    (q5,) = outcome.update.item_ids["q5"]
    (q6,) = outcome.update.item_ids["q6"]
    (parent,) = [p for p in document.parents if lead_in in body_text_lines(p.instruction)]
    assert parent.item_ids == (q5, q6)
    for item in (i for i in document.items if i.item_id in (q5, q6)):
        assert lead_in not in item.plain_text_lines()
        assert LEFT_OUT_REASON not in item.review.reasons
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert lead_in not in body_text_lines(document.instructions)
    assert native_export_blockers(document) == ()


def _anchors(entry: dict[str, JsonValue]) -> list[JsonValue]:
    value = entry["source_anchors"]
    assert isinstance(value, list)
    return list(value)


def _line_as_instruction(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """The current raw grammar reply listing q2's own line as an instruction instead."""
    items = content["items"]
    assert isinstance(items, list)
    (item,) = [
        entry for entry in items if isinstance(entry, dict) and "body:0016" in _anchors(entry)
    ]
    anchors = item["source_anchors"]
    assert isinstance(anchors, list)
    assert _GRAMMAR_LINE in anchors
    item["source_anchors"] = [anchor for anchor in anchors if anchor != _GRAMMAR_LINE]
    text = {c.anchor: c.text for c in corpus_chunks(_GRAMMAR)}[_GRAMMAR_LINE]
    instructions = content.get("instructions")
    assert isinstance(instructions, list)
    instructions.append({"text": text, "source_anchors": [_GRAMMAR_LINE], "points": None})
    return content


class _LineAsInstruction(ReplayProvider):
    """Serve the fresh grammar recording with q2's own line rewritten to an instruction."""

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
        if self.recording_ids.get(request.item_id) != _GRAPH_REPLY:
            return response
        content = copy.deepcopy(response.content)
        assert isinstance(content, dict)
        return StructuredLLMResponse(
            content=_line_as_instruction(content),
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_an_own_line_a_reply_lists_as_an_instruction_stands_at_its_place_in_the_item():
    replay = build_replay(_GRAMMAR, provider=_LineAsInstruction(_GRAMMAR))
    outcome = await replay.pipeline.convert(job=replay.job())

    lines = {c.anchor: c.text for c in corpus_chunks(_GRAMMAR)}
    assert lines[_GRAMMAR_LINE] == "Skriv NF, PF eller VF."
    (item_id,) = outcome.update.item_ids[_GRAMMAR_QUESTION]
    (item,) = [i for i in outcome.result.document.items if i.item_id == item_id]
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    printed = item.plain_text_lines()
    assert printed[0] == "Ange frastyp."
    assert printed[1] == lines[_GRAMMAR_LINE]
    assert printed[2].startswith("a) De trötta eleverna")
    assert LEFT_OUT_REASON not in item.review.reasons
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert lines[_GRAMMAR_LINE] not in body_text_lines(outcome.result.document.instructions)
