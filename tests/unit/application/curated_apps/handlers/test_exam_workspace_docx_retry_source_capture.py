"""The pipeline stores each question's retry source on its items (TASK-SKRIPT-39-05-09 D1).

Replays the repeated-conflict recording, whose q20 labeler answered ``free_text`` while the
converter first reported ``gap_fill``; the stored source must keep the labeler's first type.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v10_repeated_conflict"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_CONFLICTED = {"body:0085", "body:0086"}


async def _convert():
    replay = build_replay(_EXAM, root=_ROOT)
    return replay, await replay.pipeline.convert(job=replay.job())


async def test_every_document_item_carries_its_questions_retry_source():
    _, outcome = await _convert()

    document = outcome.update.document
    assert document.items
    for item in document.items:
        assert item.retry_source is not None, item.item_id
        assert item.retry_source.chunks, item.item_id


async def test_the_twice_conflicted_item_keeps_the_labelers_first_type():
    _, outcome = await _convert()

    kept = [item for item in outcome.update.document.items if item.source_anchor in _CONFLICTED]
    assert len(kept) == 1
    source = kept[0].retry_source
    assert source is not None
    # The first converter reply reported gap_fill; the labeler's own type was free_text.
    assert source.label_kind is NativeExamItemKind.FREE_TEXT


async def test_provisional_updates_carry_sources_for_still_converting_placeholders():
    replay, outcome = await _convert()

    first = replay.progress.updates[0]
    assert first.pending, "the first update must still hold converting questions"
    assert all(item.retry_source is not None for item in first.document.items)
    assert all(item.retry_source is not None for item in outcome.update.document.items)


async def test_the_stored_source_survives_the_persistence_round_trip():
    _, outcome = await _convert()

    document = outcome.update.document
    reopened = NativeExamDocument.model_validate(document.model_dump(mode="json"))

    assert reopened == document
    assert any(item.retry_source is not None for item in reopened.items)


async def test_own_and_key_chunks_are_pending_and_context_stays_read_only():
    _, outcome = await _convert()

    for item in outcome.update.document.items:
        source = item.retry_source
        assert source is not None
        own = {record.anchor for record in source.chunks}
        keys = {record.anchor for record in source.key_chunks}
        context = {record.anchor for record in source.context_chunks}
        assert not own & context, item.item_id
        assert not keys & context, item.item_id
