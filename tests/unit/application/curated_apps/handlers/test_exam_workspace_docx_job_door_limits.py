"""Door limits across DOCX job persistence (TASK-SKRIPT-41-01-03 B3, review F2).

A limit or cap anywhere in a DOCX job ends it as failed with the limit note: the job
keeps ``ai_limit`` and ``last_error``, the progress port abandons instead of publishing
a final document, and already-published batches stay. A completely refused first
grouping call still fails the job with the note and no published document; abandoning
with no outline is a no-op under the existing progress contract.

A busy door anywhere in a DOCX job ends it as failed with the try-again note and no
``ai_limit`` (TASK-SKRIPT-41-01-04 B7); it is never the generic crash message and never a
review item.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionOutcome,
)
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    AiJobOverageCapReached,
    ai_limit_note,
    ai_try_again_note,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_jobs import (
    JobEnvironment,
    claim,
    environment,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _RaisingPipeline:
    """Protocol-conforming double whose conversion always raises ``error``."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def convert(
        self, *, job: DocxConversionJob, fallback_reason: str | None = None
    ) -> DocxConversionOutcome:
        raise self._error


def _processor_with(env: JobEnvironment, pipeline: _RaisingPipeline):
    users = AsyncMock(get_by_id=AsyncMock(return_value=env.actor))
    return ProcessExamWorkspaceDocxJobHandler(
        jobs=env.jobs,
        chunker=PythonDocxExamChunker(),
        pipeline=pipeline,
        progress=env.replay.progress,
        store=env.store,
        users=users,
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        id_generator=env.ids,
    )


async def test_grouping_limit_fails_the_docx_job_with_the_limit_note() -> None:
    env = environment()
    env.replay.provider._failures["docx_grouping_1"] = AiDailyLimitReached(limit=AiDailyLimit.POOL)
    running = await claim(env)

    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is AiDailyLimit.POOL
    assert finished.last_error == ai_limit_note(AiDailyLimit.POOL)
    assert finished.source_docx is None
    assert env.replay.progress.calls == ["abandon"], "no outline, no batch, no final document"
    assert env.replay.progress.finals == []
    assert any(
        event.get("code") == "ai_daily_limit" and event.get("stage") == "grouping"
        for event in finished.diagnostics
    )
    assert any(
        event.get("code") == "ai_daily_limit" and event.get("stage") == "job"
        for event in finished.diagnostics
    )


async def test_limit_after_some_batches_published_keeps_batches_and_fails() -> None:
    env = environment()
    env.replay.provider._failures["docx_w1-03"] = AiDailyLimitReached(limit=AiDailyLimit.POOL)
    running = await claim(env)

    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is AiDailyLimit.POOL
    assert finished.last_error == ai_limit_note(AiDailyLimit.POOL)
    assert finished.source_docx is None
    assert env.replay.progress.calls == [
        "outline",
        "batch_ready",
        "batch_ready",
        "batch_ready",
        "abandon",
    ], "the finished batches stay published; no final document is published"
    assert env.replay.progress.finals == []
    assert len(env.replay.progress.updates) == 3, "every admitted batch reached the port"
    assert any(
        event.get("code") == "ai_daily_limit" and event.get("stage") == "batch"
        for event in finished.diagnostics
    )
    assert any(
        event.get("code") == "ai_daily_limit" and event.get("stage") == "job"
        for event in finished.diagnostics
    )


async def test_docx_job_handler_maps_an_escaped_refusal_to_limit_not_unexpected() -> None:
    env = environment()
    running = await claim(env)
    processor = _processor_with(
        env, _RaisingPipeline(AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE))
    )

    finished = await processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is AiDailyLimit.USER_SHARE
    assert finished.last_error == ai_limit_note(AiDailyLimit.USER_SHARE)
    assert any(event.get("code") == "ai_daily_limit" for event in finished.diagnostics)
    assert not any(event.get("code") == "unexpected_error" for event in finished.diagnostics)


async def test_docx_job_handler_maps_an_escaped_cap_to_overage_cap() -> None:
    env = environment()
    running = await claim(env)
    processor = _processor_with(
        env,
        _RaisingPipeline(
            AiJobOverageCapReached(overage_usd_micros=2_000_000, cap_usd_micros=1_000_000)
        ),
    )

    finished = await processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is AiDailyLimit.POOL
    assert finished.last_error == ai_limit_note(AiDailyLimit.POOL)
    assert any(event.get("code") == "ai_overage_cap" for event in finished.diagnostics)


def _assert_failed_busy(finished) -> None:
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is None
    assert finished.last_error == ai_try_again_note()
    assert finished.source_docx is None
    assert any(event.get("code") == "ai_door_busy" for event in finished.diagnostics)
    assert not any(event.get("code") == "unexpected_error" for event in finished.diagnostics)


async def test_docx_job_handler_maps_an_escaped_busy_door_to_the_try_again_note() -> None:
    env = environment()
    running = await claim(env)
    processor = _processor_with(env, _RaisingPipeline(AiDoorBusy(retry_after_seconds=3)))

    finished = await processor.handle(job=running)

    _assert_failed_busy(finished)


async def test_busy_grouping_fails_the_docx_job_with_the_try_again_note() -> None:
    env = environment()
    env.replay.provider._failures["docx_grouping_1"] = AiDoorBusy(retry_after_seconds=None)
    running = await claim(env)

    finished = await env.processor.handle(job=running)

    _assert_failed_busy(finished)
    assert env.replay.provider.requests[-1].item_id == "docx_grouping_1", "grouping is not retried"
    assert env.replay.progress.calls == ["abandon"]
    assert env.replay.progress.finals == []


async def test_busy_batch_fails_the_docx_job_instead_of_becoming_a_review_item() -> None:
    env = environment()
    env.replay.provider._failures["docx_w1-03"] = AiDoorBusy(retry_after_seconds=7)
    running = await claim(env)

    finished = await env.processor.handle(job=running)

    _assert_failed_busy(finished)
    assert "abandon" in env.replay.progress.calls
    assert env.replay.progress.finals == [], "no document is published as a completed conversion"
