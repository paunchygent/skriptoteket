"""Replays of a one-family-per-batch live run (D25, D32, D37).

``docx_build_v10_one_family`` holds the live recordings of the run in which the final course
exam crashed the whole conversion and three choice questions with a printed blank became
review items. Replies the crash cancelled were never recorded, so those batches replay as
provider failures and leave their questions as review items.
"""

import json
from typing import Any

import pytest

from skriptoteket.application.curated_apps.handlers import exam_workspace_docx_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamItemKind,
    NativeParseOrigin,
    NativeTextSegment,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v10_one_family"
_COURSE_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_CHOICE_EXAM = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"


def _text(item: NativeExamItem) -> str:
    return "\n".join(
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    )


def _starting_at(items: tuple[NativeExamItem, ...], anchor: str) -> NativeExamItem:
    found = [item for item in items if item.source_anchor == anchor]
    assert len(found) == 1, f"{anchor} must start exactly one item"
    return found[0]


async def test_an_empty_reply_body_leaves_a_review_item_and_keeps_every_other_batch():
    replay = build_replay(_COURSE_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    items = outcome.result.document.items
    assert outcome.update.pending == ()
    for anchor in ("body:0093", "body:0105", "body:0111"):
        kept = _starting_at(items, anchor)
        assert kept.review.parse_origin is NativeParseOrigin.LLM_PARSED
        assert not kept.review.reasons, f"the recorded batch converting {anchor} was lost"
    heading = _starting_at(items, "body:0085")
    assert heading.review.reasons
    assert "Huvudsats, bisats och BIFF" in _text(heading), "the review item lost its source text"
    position = {chunk.anchor: n for n, chunk in enumerate(corpus_chunks(_COURSE_EXAM))}
    anchors = [item.source_anchor for item in items]
    assert len(set(anchors)) == len(anchors), "a chunk anchor starts two items"
    assert [position[a or ""] for a in anchors] == sorted(position[a or ""] for a in anchors)


async def test_a_subpart_the_grouping_lists_only_as_a_subpart_is_converted_with_its_question():
    replay = build_replay(_COURSE_EXAM, root=_ROOT, families_per_batch=1)
    await replay.pipeline.convert(job=replay.job())

    sent = {
        request.item_id: json.loads(request.user_payload)
        for request in replay.provider.requests
        if request.item_id.startswith("docx_w")
    }

    def own_anchors(request_id: str) -> set[str]:
        return {chunk["anchor"] for chunk in sent[request_id]["chunks"]}

    assert "body:0086" in own_anchors("docx_w2-05"), "the subpart left its question's batch"
    assert "body:0086" not in own_anchors("docx_w1-02"), "the next question's batch owns it"


async def test_a_choice_question_whose_stem_holds_a_blank_converts_as_single_choice():
    replay = build_replay(_CHOICE_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    assert "native_contract_invalid" not in [e.code for e in outcome.result.events]
    for anchor, answer in (
        ("body:0007", "devoured"),
        ("body:0010", "an acquaintance"),
        ("body:0028", "collateral"),
    ):
        item = _starting_at(outcome.result.document.items, anchor)
        assert item.kind is NativeExamItemKind.SINGLE_CHOICE
        assert not item.review.reasons
        correct = [
            c.text for c in item.choices if c.choice_id in item.answer_key.correct_choice_ids
        ]
        assert correct == [answer]
        assert answer not in _text(item), "the facit answer became student-visible"


async def test_a_choice_batch_schema_offers_no_gap_segment():
    replay = build_replay(_CHOICE_EXAM, root=_ROOT, families_per_batch=1)
    await replay.pipeline.convert(job=replay.job())

    request = next(r for r in replay.provider.requests if r.item_id == "docx_w1-02")
    schema: Any = request.output_spec.json_schema
    assert schema["$defs"]["ProducedSegment"]["properties"]["kind"]["enum"] == ["text"]


async def test_an_exception_inside_one_batch_fails_only_that_batch(monkeypatch):
    convert_batch = exam_workspace_docx_pipeline.convert_batch

    async def failing_batch(**kwargs):
        if kwargs["batch"].batch_id == "w1-02":
            raise RuntimeError("unexpected failure inside the batch")
        return await convert_batch(**kwargs)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "convert_batch", failing_batch)
    replay = build_replay(_COURSE_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    items = outcome.result.document.items
    assert outcome.update.pending == ()
    failed = _starting_at(items, "body:0093")
    assert failed.review.reasons
    assert "Fråga 21. Renässansen" in _text(failed), "the failed question lost its source text"
    for anchor in ("body:0105", "body:0111"):
        assert not _starting_at(items, anchor).review.reasons
    assert "batch_failed" in [e.code for e in outcome.result.events]
    assert replay.progress.updates[-1].pending == (), "the failed batch left a placeholder"
