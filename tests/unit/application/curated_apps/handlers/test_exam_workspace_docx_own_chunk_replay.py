"""A question keeps its own chunks when a reply also lists one as an answer key.

``docx_build_v16_low19_own_chunk`` holds unedited live recordings of a one-family-per-batch
run. The grouping lists body:0086 among one question's own chunks, not among its answer keys,
and the converter reply for that question lists body:0086 both in ``answer_key_anchors`` and in
the item's source_anchors, with body:0087. The chunk stays with the item and is never a
teacher note. The reply's item prints the facit as text and has no gap, so the native contract
turns it into a review item; that review item shows every chunk the item lists, body:0086
included.
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

_ROOT = FIXTURES / "docx_build_v16_low19_own_chunk"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_OWN = ["body:0085", "body:0086"]


def _grouped_question() -> dict[str, object]:
    questions = recording(_EXAM, "docx_grouping_1", root=_ROOT)["questions"]
    assert isinstance(questions, list)
    (question,) = [q for q in questions if isinstance(q, dict) and "body:0086" in q["anchors"]]
    return question


async def test_a_question_s_own_chunk_a_reply_also_lists_as_an_answer_key_stays_with_its_item():
    question = _grouped_question()
    assert question["anchors"] == _OWN
    assert "body:0086" not in question["answer_key_anchors"]
    reply = recording(_EXAM, "docx_w2-09-01", root=_ROOT)
    assert reply["answer_key_anchors"] == ["body:0086"]
    items = reply["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    assert items[0]["source_anchors"] == [*_OWN, "body:0087"]

    provider = SecondWaveByAnchor(_EXAM, root=_ROOT)
    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    texts = {c.anchor: c.text for c in corpus_chunks(_EXAM)}
    (item,) = [i for i in outcome.result.document.items if i.source_anchor == "body:0085"]
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    shown = [s.text for p in item.body for s in p.segments if isinstance(s, NativeTextSegment)]
    assert shown == [texts[a] for a in (*_OWN, "body:0087")]
    assert texts["body:0086"] not in outcome.result.notes
