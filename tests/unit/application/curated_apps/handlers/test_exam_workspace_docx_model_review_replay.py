"""A question the model marks for review shows its source as printed (D32, user decision
2026-10-11).

``docx_build_v12_low14_model_review`` holds the live recordings of a one-family-per-batch run
in which the model returned ``outcome: review`` for a question whose lettered parts carry their
answers inline. The review item holds every chunk the question owns, in source order, facit
included, under the same section parent as the converted question would be, and the document
stays blocked for export while it is there.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
    native_export_blockers,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v12_low14_model_review"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = ("body:0085", "body:0086", "body:0087")
_PREVIOUS_QUESTION = "body:0079"


def _paragraphs(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


async def test_a_model_review_item_shows_every_source_chunk_of_its_question_in_order():
    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    by_anchor = {item.source_anchor: item for item in document.items}
    item = by_anchor[_QUESTION[0]]
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.review.reasons == (
        "AI-tolkningen markerade frågan för granskning: "
        "Uppgiften saknar en tydlig instruktion eller fråga.",
    )
    assert _paragraphs(item) == [text[anchor] for anchor in _QUESTION]
    assert item.title is None, "the review item shows a generated title"
    assert item.points is None, "the review item shows generated points beside the printed line"
    previous = by_anchor[_PREVIOUS_QUESTION]
    assert not previous.review.reasons
    assert document.parent_of(item.item_id) == document.parent_of(previous.item_id)
    assert ("review_required", item.item_id) in {
        (blocker.reason, blocker.item_id) for blocker in native_export_blockers(document)
    }
    events = [e for e in outcome.result.events if e.code == "model_review"]
    assert [e.anchors for e in events] == [_QUESTION]
    assert outcome.update.pending == ()
