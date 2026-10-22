"""Door limits across the DOCX conversion pipeline (TASK-SKRIPT-41-01-03 B3).

Proves the limit rule for multi-call jobs through a synthetic four-question exam over a
scripted provider door: a refused batch fails only its items and stops later calls, a
content refusal keeps the conversion, a grouping refusal fails everything pending, the
overage cap stops the crossing call itself, and a job admitted before the pool ran out
finishes as paid overage while the next job is refused at grouping. A busy door is no
limit: a busy grouping or batch call stops the conversion with ``AiDoorBusy`` instead of
becoming a review item, and busy optional content tags drop silently.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.llm_door import AiDailyLimit, AiDoorBusy
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.llm_door import DoorOperation
from tests.unit.application.curated_apps.handlers.docx_door_limit_support import (
    DoorScript,
    batch_anchors,
    convert,
    convert_with,
    exam_bytes,
    grouping_for,
    sent_batches,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_batch_limit_fails_only_that_batch_and_stops_later_calls(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    anchors = [chunk.anchor for chunk in chunks]
    script = DoorScript(grouping=grouping_for(anchors), refuse_batch_calls=(2,))
    outcome, _ = await convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert outcome.result.ai_limit is AiDailyLimit.POOL
    assert [event.code for event in outcome.result.events].count("ai_daily_limit") >= 1
    batch_payloads = sent_batches(script)
    assert len(batch_payloads) == 2, "the first batch and the refused second call; the rest stop"
    sent_anchors = {
        anchor
        for payload in batch_payloads
        for question in batch_anchors(payload)
        for anchor in question
    }
    assert anchors[3] not in sent_anchors, "the third batch makes no door call"
    question_anchors = set(anchors[1:])
    converted = [item for item in outcome.result.document.items if not item.review.reasons]
    assert {item.source_anchor for item in converted} == {anchors[1]}, "the finished batch is kept"
    review_anchors = {
        item.source_anchor for item in outcome.result.document.items if item.review.reasons
    }
    assert set(anchors[2:]) <= review_anchors, "the refused batch items carry review reasons"
    assert question_anchors <= {item.source_anchor for item in outcome.result.document.items}
    assert outcome.update.pending == ()


async def test_content_limit_keeps_the_conversion_and_records_the_limit(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    script = DoorScript(grouping=grouping_for([c.anchor for c in chunks]), refuse_content=True)
    outcome, _ = await convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.USER_SHARE
    assert outcome.limit_code == "ai_daily_limit"
    assert outcome.result.document.items, "the conversion completes instead of crashing"
    assert outcome.result.document.header.tags == ()


async def test_grouping_limit_fails_all_pending_with_ai_limit(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    script = DoorScript(grouping=grouping_for([c.anchor for c in chunks]), refuse_grouping=True)
    outcome, _ = await convert_with(script, monkeypatch)

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert outcome.limit_code == "ai_daily_limit"
    assert script.door.sent and len(script.door.sent) == 1, "grouping is never retried"
    assert [(e.stage, e.code) for e in outcome.result.events if e.code == "ai_daily_limit"] == [
        ("grouping", "ai_daily_limit")
    ]
    assert outcome.result.document.items, "pending questions become review items"
    assert outcome.update.pending == ()


async def test_overage_under_one_usd_finishes_without_limit(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    script = DoorScript(
        grouping=grouping_for([c.anchor for c in chunks]), batch_charge_usd_micros=100_000
    )
    outcome, job = await convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is None
    batch_responses = [s for s in script.door.sent if s.operation is DoorOperation.RESPONSES]
    assert len(batch_responses) == 5, "grouping plus all four batches run"
    assert job.caller.overage_usd_micros == 400_000
    assert outcome.result.document.header.tags, "content tags still land"


async def test_overage_past_one_usd_stops_the_crossing_call(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    anchors = [chunk.anchor for chunk in chunks]
    script = DoorScript(grouping=grouping_for(anchors), batch_charge_usd_micros=600_000)
    outcome, job = await convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert outcome.limit_code == "ai_overage_cap"
    assert job.caller.overage_usd_micros == 1_200_000
    assert [e.code for e in outcome.result.events].count("ai_overage_cap") >= 1
    batch_payloads = sent_batches(script)
    assert len(batch_payloads) == 2, "the first batch and the crossing call; the rest stop"
    sent_anchors = {
        anchor
        for payload in batch_payloads
        for question in batch_anchors(payload)
        for anchor in question
    }
    assert anchors[3] not in sent_anchors, "the third batch reaches no batch call"
    assert anchors[4] not in sent_anchors, "the fourth batch makes no door call"
    converted = [
        item
        for item in outcome.result.document.items
        if item.source_anchor in anchors[1:] and not item.review.reasons
    ]
    assert len(converted) == 1, "only the finished batch is kept, the rest are review"
    assert outcome.update.pending == ()


async def test_overage_crossed_by_the_final_batch_call_stops_the_job(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    anchors = [chunk.anchor for chunk in chunks]
    script = DoorScript(grouping=grouping_for(anchors), batch_charge_usd_micros=300_000)
    outcome, job = await convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert outcome.limit_code == "ai_overage_cap"
    assert job.caller.overage_usd_micros == 1_200_000
    assert [e.code for e in outcome.result.events].count("ai_overage_cap") >= 1
    batch_payloads = sent_batches(script)
    assert len(batch_payloads) == 4, "every batch reaches the door; the last crossing call raises"
    converted = [
        item
        for item in outcome.result.document.items
        if item.source_anchor in anchors[1:] and not item.review.reasons
    ]
    assert len(converted) == 3, "the three finished batches are kept, the last is review"
    assert outcome.update.pending == ()


async def test_started_conversion_finishes_as_overage_then_next_is_refused_at_grouping(
    monkeypatch,
) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    grouping = grouping_for([c.anchor for c in chunks])
    script = DoorScript(grouping=grouping, refuse_non_overage_after_first=True)

    first_outcome, _ = await convert_with(script, monkeypatch, course_key="SVESVE02")
    assert first_outcome.ai_limit is None
    assert first_outcome.result.document.header.tags, "content tags land as overage"
    assert [s.allow_paid_overage for s in script.door.sent][0] is False
    assert all(s.allow_paid_overage for s in script.door.sent[1:])
    first_sent = len(script.door.sent)

    second_pipeline, second_job = convert(script, course_key="SVESVE02")
    second_outcome = await second_pipeline.convert(job=second_job)
    assert second_outcome.ai_limit is AiDailyLimit.POOL
    assert second_outcome.limit_code == "ai_daily_limit"
    assert len(script.door.sent) == first_sent + 1, "only the refused grouping call"
    assert second_outcome.result.document.items
    assert all(item.review.reasons for item in second_outcome.result.document.items)


async def test_busy_grouping_propagates_and_is_never_retried(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    script = DoorScript(grouping=grouping_for([c.anchor for c in chunks]), busy_grouping=True)

    with pytest.raises(AiDoorBusy):
        await convert_with(script, monkeypatch)

    assert len(script.door.sent) == 1, "grouping is not retried against a busy door"


async def test_busy_batch_stops_the_conversion_instead_of_becoming_a_review_item(
    monkeypatch,
) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    script = DoorScript(grouping=grouping_for([c.anchor for c in chunks]), busy_batch_calls=(2,))

    with pytest.raises(AiDoorBusy) as caught:
        await convert_with(script, monkeypatch, course_key="SVESVE02")

    assert caught.value.retry_after_seconds == 6


async def test_busy_content_tags_drop_silently_and_keep_the_conversion(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=exam_bytes())
    grouping = grouping_for([c.anchor for c in chunks])
    baseline, _ = await convert_with(
        DoorScript(grouping=grouping), monkeypatch, course_key="SVESVE02"
    )
    outcome, _ = await convert_with(
        DoorScript(grouping=grouping, busy_content=True), monkeypatch, course_key="SVESVE02"
    )

    assert outcome.ai_limit is None
    assert outcome.limit_code is None
    assert outcome.result.document.header.tags == ()
    assert [i.source_anchor for i in outcome.result.document.items if i.review.reasons] == [
        i.source_anchor for i in baseline.result.document.items if i.review.reasons
    ], "the busy tags add no review item"
