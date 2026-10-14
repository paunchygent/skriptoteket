"""A question the second pass leaves unresolved converts with its first-pass label (D23).

The fresh grammar-exam recording escalates q2 to the second pass, where it returns
``gap_fill``. This test serves the same recording with that label rewritten to
``unresolved`` in memory (explicitly synthetic): the converter batches the question with the
first pass's top label, so it reaches a gap_fill batch and converts, never a free_text one.
"""

from __future__ import annotations

import json

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
)
from skriptoteket.protocols.item_type_labeler import ItemTypeLabel
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_grammatik_omprov_variant_1_med_facit"
_QUESTION = "q2"
_OWN = ("body:0016", "body:0017")


class _UnresolvedLabel(ReplayProvider):
    """Serve the fresh recordings with q2's second-pass label rewritten to unresolved."""

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(request=request, profile=profile)
        if request.item_id != "label_b:q2":
            return response
        return StructuredLLMResponse(
            content={"label": ItemTypeLabel.UNRESOLVED.value},
            finish_reason=response.finish_reason,
            usage=response.usage,
        )


async def test_an_unresolved_second_pass_label_converts_in_the_first_pass_label_batch():
    provider = _UnresolvedLabel(_EXAM)
    replay = build_replay(_EXAM, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    assert "label_b:q2" in provider.request_ids
    holding = [
        json.loads(request.user_payload)["item_kinds"]
        for request in provider.requests
        if request.item_id.startswith("docx_w2")
        and set(_OWN) & {chunk["anchor"] for chunk in json.loads(request.user_payload)["chunks"]}
    ]
    assert holding == [[ItemTypeLabel.GAP_FILL.value]]
    (item_id,) = outcome.update.item_ids[_QUESTION]
    (item,) = [i for i in outcome.result.document.items if i.item_id == item_id]
    assert item.kind is NativeExamItemKind.GAP_FILL
    assert not item.review.reasons
