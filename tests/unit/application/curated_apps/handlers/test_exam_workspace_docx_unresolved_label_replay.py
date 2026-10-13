"""A question the second pass leaves unresolved converts with its first-pass label (D23).

``docx_build_v14_low17_unresolved_label`` holds the unedited live recordings of a
one-family-per-batch run. The first pass labels the question holding body:0086 gap_fill below
the acceptance threshold, and the second pass answers unresolved. The question must reach a
gap_fill batch, where the type_conflict resend can still correct a wrong label, and never a
free_text batch.
"""

import json

import pytest

from skriptoteket.protocols.item_type_labeler import ItemTypeLabel
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v14_low17_unresolved_label"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = "q20"
_STEM = "body:0086"


async def test_an_unresolved_second_pass_label_converts_in_the_first_pass_label_batch():
    assert recording(_EXAM, f"label_b_{_QUESTION}", root=_ROOT) == {
        "label": ItemTypeLabel.UNRESOLVED.value
    }

    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1)
    await replay.pipeline.convert(job=replay.job())

    batches = [
        json.loads(request.user_payload)
        for request in replay.provider.requests
        if request.item_id.startswith("docx_w")
    ]
    holding = [
        payload["item_kinds"]
        for payload in batches
        if _STEM in {chunk["anchor"] for chunk in payload["chunks"]}
    ]
    assert holding == [[ItemTypeLabel.GAP_FILL.value]]
