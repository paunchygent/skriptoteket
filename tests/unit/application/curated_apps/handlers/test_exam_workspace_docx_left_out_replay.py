"""A converted item that leaves out some of its question's own chunks carries a check mark.

``docx_build_v16_low22_left_out`` holds unedited live replies of a one-family-per-batch run (see
its README). The item stays converted and carries a check mark showing the left-out chunks as
printed (D41). Those chunks are not separate review items, and export stays blocked until the
teacher marks the item reviewed, which the item editor saves as ``review_complete``.
"""

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeExportBlocker,
    NativeItemReviewState,
    NativeParseOrigin,
    native_exam_document_json_bytes,
    native_export_blockers,
    parse_native_exam_document,
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


async def test_a_converted_item_leaving_out_own_chunks_shows_them_in_its_check_mark():
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
    texts = {c.anchor: c.text for c in corpus_chunks(_EXAM)}
    (item,) = [i for i in document.items if i.source_anchor == "body:0025"]
    assert item.kind is NativeExamItemKind.GAP_FILL
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons[-4:] == (
        LEFT_OUT_REASON,
        texts["body:0027"],
        texts["body:0028"],
        texts["body:0029"],
    )
    left_out = {"body:0027", "body:0028", "body:0029"}
    assert all(i.source_anchor not in left_out for i in document.items)
    blocker = NativeExportBlocker(item_id=item.item_id, reason="review_required")
    assert blocker in native_export_blockers(document)

    review = item.review.model_copy(update={"state": NativeItemReviewState.REVIEW_COMPLETE})
    reviewed = item.model_copy(update={"review": review})
    updated = tuple(reviewed if i is item else i for i in document.items)
    saved = native_exam_document_json_bytes(document.model_copy(update={"items": updated}))
    assert all(
        b.item_id != item.item_id for b in native_export_blockers(parse_native_exam_document(saved))
    )
