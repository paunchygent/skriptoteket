"""The pipeline stores each question's retry source on its items (TASK-SKRIPT-39-05-09 D1).

The fresh grammar-exam replay is clean: every item, converted or review, carries its
question's retry source with own, key and context chunks apart, and the source survives the
persistence round trip. The fresh english-exam replay holds one question whose producer
reply the provenance validator refuses; its review item still carries the type the second
labeling pass left, not the review kind.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_GRAMMAR = "svenska_2_grammatik_omprov_variant_1_med_facit"
_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_REFUSED = "body:0115"


async def test_every_document_item_carries_its_questions_retry_source():
    replay = build_replay(_GRAMMAR)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.update.document
    assert document.items
    for item in document.items:
        assert item.retry_source is not None, item.item_id
        assert item.retry_source.chunks, item.item_id
        own = {record.anchor for record in item.retry_source.chunks}
        keys = {record.anchor for record in item.retry_source.key_chunks}
        context = {record.anchor for record in item.retry_source.context_chunks}
        assert own, item.item_id
        assert not own & context, item.item_id
        assert not keys & context, item.item_id
        assert not own & keys, item.item_id


async def test_provisional_updates_carry_sources_for_still_converting_placeholders():
    replay = build_replay(_GRAMMAR)
    outcome = await replay.pipeline.convert(job=replay.job())

    first = replay.progress.updates[0]
    assert first.pending, "the first update must still hold converting questions"
    assert all(item.retry_source is not None for item in first.document.items)
    assert all(item.retry_source is not None for item in outcome.update.document.items)


async def test_the_stored_source_survives_the_persistence_round_trip():
    replay = build_replay(_GRAMMAR)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.update.document
    reopened = NativeExamDocument.model_validate(document.model_dump(mode="json"))
    assert reopened == document
    assert any(item.retry_source is not None for item in reopened.items)


async def test_a_refused_reply_keeps_the_labelers_kind_in_its_retry_source():
    replay = build_replay(_ENGLISH)
    outcome = await replay.pipeline.convert(job=replay.job())

    item = next(i for i in outcome.update.document.items if i.source_anchor == _REFUSED)
    assert item.kind is NativeExamItemKind.FREE_TEXT, "the refused item became a review item"
    assert item.review.reasons
    assert item.retry_source is not None
    assert item.retry_source.label_kind is NativeExamItemKind.GAP_FILL, (
        "the stored source must keep the labeler's type"
    )
