"""Door limits across the content-suggestion job (TASK-SKRIPT-41-01-03 B3).

A refused suggestion fails the job with the limit and its teacher note; a missing owner
fails without calling the classifier. The handler itself is owned by R3: the note
assertions below fail until that repair lands.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    content_response,
)
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiJobOverageCapReached,
    ai_limit_note,
)
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    InMemoryEnrichmentJobRepository,
)
from tests.unit.application.curated_apps.handlers.docx_door_limit_support import (
    content_handler,
    content_job,
    failing_classifier,
    run_content_job,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_content_job_limit_fails_with_the_limit_note() -> None:
    classifier = failing_classifier(AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE))
    finished = await run_content_job(classifier=classifier)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_daily_limit"
    assert finished.ai_limit is AiDailyLimit.USER_SHARE
    assert classifier.suggest.await_count == 1
    assert content_response(finished).message == ai_limit_note(AiDailyLimit.USER_SHARE)


async def test_content_job_overage_cap_fails_with_pool_limit() -> None:
    classifier = failing_classifier(
        AiJobOverageCapReached(overage_usd_micros=2_000_000, cap_usd_micros=1_000_000)
    )
    finished = await run_content_job(classifier=classifier)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_overage_cap"
    assert finished.ai_limit is AiDailyLimit.POOL
    assert classifier.suggest.await_count == 1
    assert content_response(finished).message == ai_limit_note(AiDailyLimit.POOL)


async def test_content_job_without_owner_fails_owner_missing() -> None:
    classifier = AsyncMock()
    jobs = InMemoryEnrichmentJobRepository()
    job, _ = content_job(owner_id=uuid4())
    await jobs.create(job=job)
    handler = content_handler(classifier=classifier, jobs=jobs, users=UserRepositoryStub())

    finished = await handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "owner_missing"
    classifier.suggest.assert_not_awaited()
