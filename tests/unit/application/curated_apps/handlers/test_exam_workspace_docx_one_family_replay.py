"""One batch's fault stays inside it, subparts stay with their question, and the batch schema
narrows the kinds it admits (D2, D3, D25).

The fresh course-exam replay carries context chunks owned by a question (body:0062 for q16)
and a subpart (body:0086 for q20). A question reaches the batch with its own chunks; the
choice batch's schema offers no gap segment; and an exception inside one batch leaves only
that batch's questions as review items holding their source text, while every other batch
still converts.
"""

import pytest

from skriptoteket.application.curated_apps.handlers import exam_workspace_docx_pipeline
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import BatchOutcome
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_BATCH_FAILED_REASON = "Frågan kunde inte tolkas. Kontrollera källtexten manuellt."


async def test_a_subpart_stays_with_the_question_that_owns_it():
    replay = build_replay(_EXAM)
    outcome = await replay.pipeline.convert(job=replay.job())

    (q20_item_id,) = [
        item_id
        for item_id in outcome.update.item_ids["q20"]
        if next(i for i in outcome.result.document.items if i.item_id == item_id).source_anchor
        == "body:0085"
    ]
    (item,) = [i for i in outcome.result.document.items if i.item_id == q20_item_id]
    printed = item.plain_text_lines()
    assert any("De väntar inte." in line for line in printed)
    assert any("att de inte väntar" in line for line in printed)
    assert all(
        not any("De väntar inte." in line for line in other.plain_text_lines())
        for other in outcome.result.document.items
        if other.item_id != q20_item_id
    )


async def test_a_choice_batch_schema_offers_no_gap_segment():
    replay = build_replay(_EXAM)
    await replay.pipeline.convert(job=replay.job())

    request = next(r for r in replay.provider.requests if r.item_id == "docx_w1-01")
    definitions = request.output_spec.json_schema["$defs"]
    assert isinstance(definitions, dict)
    segment = definitions["ProducedSegment"]
    assert isinstance(segment, dict)
    segment_properties = segment["properties"]
    assert isinstance(segment_properties, dict)
    segment_kind = segment_properties["kind"]
    assert isinstance(segment_kind, dict)
    kinds = segment_kind["enum"]
    assert isinstance(kinds, list)
    assert kinds == ["text"]
    item = definitions["ProducedItem"]
    assert isinstance(item, dict)
    item_properties = item["properties"]
    assert isinstance(item_properties, dict)
    item_kind = item_properties["kind"]
    assert isinstance(item_kind, dict)
    item_kinds = item_kind["enum"]
    assert isinstance(item_kinds, list)
    assert set(item_kinds) == {"single_choice", "multiple_response"}


async def test_an_exception_inside_one_batch_fails_only_that_batch(monkeypatch):
    convert_batch = exam_workspace_docx_pipeline.convert_batch

    async def failing_batch(
        *,
        state: DocxBuildState,
        batch: ConversionBatch,
        families: dict[str, QuestionFamily],
        exchange: DocxBuildRoundExchange,
        profile: StructuredLLMProviderProfile,
    ) -> BatchOutcome:
        if batch.batch_id == "w1-02":
            raise RuntimeError("unexpected failure inside the batch")
        return await convert_batch(
            state=state, batch=batch, families=families, exchange=exchange, profile=profile
        )

    monkeypatch.setattr(exam_workspace_docx_pipeline, "convert_batch", failing_batch)
    replay = build_replay(_EXAM)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    assert outcome.update.pending == ()
    blocked = {blocker.item_id for blocker in native_export_blockers(document)}
    for anchor in ("body:0061", "body:0067", "body:0073", "body:0079", "body:0085"):
        (item,) = [i for i in document.items if i.source_anchor == anchor]
        assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert item.review.reasons == (_BATCH_FAILED_REASON,)
        assert item.item_id in blocked, "a failed review item does not block export"
    subpart = next(i for i in document.items if i.source_anchor == "body:0085")
    assert any("att de inte väntar" in line for line in subpart.plain_text_lines()), (
        "the failed question lost its subpart"
    )
    (kept_id,) = outcome.update.item_ids["q1"]
    (kept,) = [i for i in document.items if i.item_id == kept_id]
    assert not kept.review.reasons
    assert "batch_failed" in [e.code for e in outcome.result.events]
    assert replay.progress.updates[-1].pending == (), "the failed batch left a placeholder"
