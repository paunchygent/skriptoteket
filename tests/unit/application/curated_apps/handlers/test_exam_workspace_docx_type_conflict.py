"""A question that conflicts twice is resent once, then kept as converted with the type mark.

Replays the recordings of ``docx_build_v10_repeated_conflict`` (one second-pass reply edited,
see its README), where batch ``w2-05-01`` reports a type conflict and its resend
``w2-05-01c01`` reports one again.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v10_repeated_conflict"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_CONFLICTED = {"body:0085", "body:0086"}


async def _convert():
    replay = build_replay(_EXAM, root=_ROOT)
    return replay, await replay.pipeline.convert(job=replay.job())


async def test_a_second_type_conflict_is_not_resent_again():
    replay, outcome = await _convert()

    ids = replay.provider.request_ids
    assert ids.count("docx_w2-05-01") == 1
    assert ids.count("docx_w2-05-01c01") == 1
    assert "docx_w2-05-01c01c01" not in ids
    assert outcome.update.pending == ()


async def test_the_twice_conflicted_family_is_kept_as_converted_with_the_type_mark():
    replay, outcome = await _convert()

    resend = recording(_EXAM, "docx_w2-05-01c01", _ROOT)["items"]
    assert isinstance(resend, list) and isinstance(resend[0], dict)
    source_kind = NativeExamItemKind(str(resend[0]["conflict_kind"]))
    document = outcome.update.document
    kept = [i for i in document.items if i.source_anchor in _CONFLICTED]
    assert len(kept) == 1, "the conflicted chunks must start exactly one item"
    item = kept[0]

    assert item.kind is source_kind
    assert not item.review.reasons
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.review.confidence is not None and item.review.confidence < 0.95
    codes = [e.code for e in outcome.result.events]
    assert codes.count("type_conflict_kept") == 1
    assert codes.count("type_conflict") == 1, "only the first reply may report a conflict"
    assert not [
        i
        for i in document.items
        if i.source_anchor in _CONFLICTED and any("svarstyp" in r for r in i.review.reasons)
    ], "a chunk of the family became a review item with the old conflict reason"


async def test_every_grouped_question_still_maps_to_items_with_no_shared_anchor():
    _, outcome = await _convert()
    update = outcome.update
    document = update.document

    assert update.pending == ()
    assert all(update.item_ids[qid] for qid in update.item_ids), "a question lost all its items"
    mapped = [item_id for ids in update.item_ids.values() for item_id in ids]
    mapped += update.extra_item_ids
    assert sorted(mapped) == sorted(item.item_id for item in document.items)
    anchors = [item.source_anchor for item in document.items]
    assert len(set(anchors)) == len(anchors), "a chunk anchor starts two items"
    position = {c.anchor: n for n, c in enumerate(corpus_chunks(_EXAM))}
    assert [position[a or ""] for a in anchors] == sorted(position[a or ""] for a in anchors)
