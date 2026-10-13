"""A converted item that leaves out own chunks whose wording it copies carries no check mark.

``docx_build_v16_low22_left_out`` holds unedited live replies of a one-family-per-batch run (see
its README). The reply lists only the first sub-question's anchor but copies every sub-question
into its body. The item holds the left-out chunks (D41); they are not separate review items, and
because the item holds their wording it needs no review and nothing blocks its export (D4, D1).
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    SecondWaveByAnchor,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v16_low22_left_out"
_EXAM = "svenska_2_grammatik_omprov_variant_1_med_facit"


async def test_a_converted_item_copying_the_wording_of_left_out_chunks_is_not_flagged():
    questions = recording(_EXAM, "docx_grouping_1", root=_ROOT)["questions"]
    assert isinstance(questions, list)
    (question,) = [
        q
        for q in questions
        if isinstance(q, dict) and isinstance(q["anchors"], list) and "body:0025" in q["anchors"]
    ]
    assert question["anchors"] == [f"body:{n:04d}" for n in range(25, 30)]
    items = recording(_EXAM, "docx_w2-03-01", root=_ROOT)["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    assert items[0]["source_anchors"] == ["body:0025", "body:0026", "body:0030"]

    provider = SecondWaveByAnchor(_EXAM, root=_ROOT)
    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    assert len(document.items) == 8
    (item,) = [i for i in document.items if i.source_anchor == "body:0025"]
    assert item.kind is NativeExamItemKind.GAP_FILL
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()
    left_out = {"body:0027", "body:0028", "body:0029"}
    assert all(i.source_anchor not in left_out for i in document.items)
    texts = {c.anchor: c.text for c in corpus_chunks(_EXAM)}
    stems = " ".join(
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if segment.kind == "text"
    )
    assert all(texts[a].split(" Huvudord:")[0] in stems for a in left_out)
    assert all(b.item_id != item.item_id for b in native_export_blockers(document))
