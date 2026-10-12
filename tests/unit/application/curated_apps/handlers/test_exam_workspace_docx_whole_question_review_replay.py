"""A review item built from a failed converter item holds the whole question.

``docx_build_v16_low19_partial_review`` holds live recordings of a one-family-per-batch run,
edited so that a gapless gap_fill item lists only body:0085 and body:0087 while the grouping
gives the question body:0085 and body:0086 and the reply lists body:0086 as an answer key (see
its README). The item fails the native contract; its review item shows every own chunk of the
question and every chunk the item lists, in source order, facit included.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeParseOrigin,
    NativeTextSegment,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    SecondWaveByAnchor,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v16_low19_partial_review"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"


async def test_a_failed_item_listing_part_of_its_question_becomes_a_review_item_of_the_whole():
    questions = recording(_EXAM, "docx_grouping_1", root=_ROOT)["questions"]
    assert isinstance(questions, list)
    (question,) = [
        q
        for q in questions
        if isinstance(q, dict) and isinstance(q["anchors"], list) and "body:0085" in q["anchors"]
    ]
    assert question["anchors"] == ["body:0085", "body:0086"]
    reply = recording(_EXAM, "docx_w2-09-01", root=_ROOT)
    items = reply["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    assert items[0]["source_anchors"] == ["body:0085", "body:0087"]

    provider = SecondWaveByAnchor(_EXAM, root=_ROOT)
    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    texts = {c.anchor: c.text for c in corpus_chunks(_EXAM)}
    (item,) = [i for i in outcome.result.document.items if i.source_anchor == "body:0085"]
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    shown = [s.text for p in item.body for s in p.segments if isinstance(s, NativeTextSegment)]
    assert shown == [texts[a] for a in ("body:0085", "body:0086", "body:0087")]
    others = [i for i in outcome.result.document.items if i is not item]
    assert all(i.source_anchor not in {"body:0086", "body:0087"} for i in others)
