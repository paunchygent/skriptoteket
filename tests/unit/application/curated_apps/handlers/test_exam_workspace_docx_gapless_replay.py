"""Replay of a one-family live run in which a gap_fill reply placed no gap (D32).

``docx_build_v10_low8_gapless`` holds the recordings of the run in which the batch for the
last linking-word question dropped the blank that opens its sentence and returned a
gap_fill item with text segments only. The item cannot be built, so it is a review item
holding its source text, and its reason names the invariant it breaks.
"""

import pytest

from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v10_low8_gapless"
_CHOICE_EXAM = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"
_GAPLESS = "body:0168"
_INVARIANT = "gap_fill items need at least one gap"


async def test_a_gap_fill_reply_without_a_gap_is_a_review_item_naming_the_invariant():
    replay = build_replay(_CHOICE_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    events = [
        event
        for event in outcome.result.events
        if event.code == "native_contract_invalid" and _GAPLESS in event.anchors
    ]
    assert len(events) == 1
    assert _INVARIANT in events[0].detail
    item = next(i for i in outcome.result.document.items if i.source_anchor == _GAPLESS)
    assert any(_INVARIANT in reason for reason in item.review.reasons)
