"""A question the model marks for review shows its source as printed (D32, user decision
2026-10-11).

``docx_build_v12_low14_model_review`` holds the live recordings of a one-family-per-batch run
in which the model returned ``outcome: review`` for a question whose lettered parts carry their
answers inline. The review item holds every chunk the question owns, in source order, facit
included, between its neighbouring questions. The grouping gives no shared context governing
two or more of those three questions; the printed section headings still parent them, the
review item included (T2, D27). The document stays blocked for export while the review
item is there.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v12_low14_model_review"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_QUESTION = ("body:0085", "body:0086", "body:0087")
_PREVIOUS_QUESTION = "body:0079"
_NEXT_QUESTION = "body:0093"
_SECTION = ("q19", "q20", "q21")


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
    assert not hasattr(item, "title"), "items carry no title (39-05-08)"
    # The source-text fallback keeps the question's printed points (O3, 39-05-08).
    assert item.points == 2
    previous, following = by_anchor[_PREVIOUS_QUESTION], by_anchor[_NEXT_QUESTION]
    assert not previous.review.reasons and not following.review.reasons
    assert previous.sequence + 1 == item.sequence == following.sequence - 1
    contexts = recording(_EXAM, "docx_grouping_1", root=_ROOT)["shared_contexts"]
    assert isinstance(contexts, list)
    shared = [
        c
        for c in contexts
        if isinstance(c, dict)
        and isinstance(c["governs"], list)
        and len(set(c["governs"]) & set(_SECTION)) >= 2
    ]
    assert shared == [], "the grouping governs this section; assert its parent instead"
    # The printed section headings parent the questions, the review item included
    # (T2, D27): the review item and its predecessor share the Del 2 parent, and the
    # following question opens Del 3.
    parents = [document.parent_of(i.item_id) for i in (previous, item, following)]
    assert parents[0] is not None and parents[0] == parents[1]
    assert body_text_lines(parents[0].instruction) == ("Del 2: grammatik och språkstrukturer",)
    assert parents[2] is not None and body_text_lines(parents[2].instruction) == (
        "Del 3: kortsvar",
    )
    assert ("unbuilt_question", item.item_id) in {
        (blocker.reason, blocker.item_id) for blocker in native_export_blockers(document)
    }
    events = [e for e in outcome.result.events if e.code == "model_review"]
    assert [e.anchors for e in events] == [_QUESTION]
    assert outcome.update.pending == ()
