from __future__ import annotations

from datetime import timedelta
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dishka import AsyncContainer

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.workers.exam_answer_key_enrichment import process_next_answer_key_enrichment_job
from tests.unit.workers.execution_queue_job_processor_test_support import (
    DEFAULT_NOW,
    ContainerAdapter,
    FakeClock,
    FakeUow,
)

WORKER_ID = "docx-worker"
LEASE_TTL = timedelta(seconds=30)


@pytest.fixture
def claimed_docx_job() -> ExamAnswerKeyEnrichmentJob:
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        input_filename="exam.docx",
        source_docx=b"docx source",
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        attempts=1,
        available_at=DEFAULT_NOW,
        locked_by=WORKER_ID,
        locked_until=DEFAULT_NOW + LEASE_TTL,
        created_at=DEFAULT_NOW,
        updated_at=DEFAULT_NOW,
    )


@pytest.fixture
def worker_harness() -> tuple[AsyncContainer, AsyncMock, AsyncMock]:
    jobs = AsyncMock(spec=ExamAnswerKeyEnrichmentJobRepositoryProtocol)
    handler = AsyncMock(spec=ProcessExamAnswerKeyEnrichmentJobHandler)
    handler.fail_next_expired.return_value = None
    jobs.claim_next.return_value = None
    container = ContainerAdapter(
        {
            UnitOfWorkProtocol: FakeUow(),
            ExamAnswerKeyEnrichmentJobRepositoryProtocol: jobs,
            ProcessExamAnswerKeyEnrichmentJobHandler: handler,
        }
    )
    return cast(AsyncContainer, container), jobs, handler


def expected_claim_arguments(*, enrichment_enabled: bool) -> dict[str, object]:
    arguments: dict[str, object] = {
        "worker_id": WORKER_ID,
        "now": DEFAULT_NOW,
        "lease_ttl": LEASE_TTL,
    }
    if not enrichment_enabled:
        arguments["source_kind"] = ExamAnswerKeySourceKind.DOCX_IMPORT
    return arguments


@pytest.mark.asyncio
@pytest.mark.parametrize("enrichment_enabled", [False, True])
async def test_claimed_docx_is_processed(
    enrichment_enabled: bool,
    worker_harness: tuple[AsyncContainer, AsyncMock, AsyncMock],
    claimed_docx_job: ExamAnswerKeyEnrichmentJob,
) -> None:
    container, jobs, handler = worker_harness
    jobs.claim_next.return_value = claimed_docx_job
    handler.handle.return_value = claimed_docx_job.model_copy(
        update={"status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, "source_docx": None}
    )

    processed = await process_next_answer_key_enrichment_job(
        container=container,
        worker_id=WORKER_ID,
        now=DEFAULT_NOW,
        lease_ttl=LEASE_TTL,
        clock=FakeClock(now=DEFAULT_NOW),
        enrichment_enabled=enrichment_enabled,
    )

    assert processed is True
    arguments = expected_claim_arguments(enrichment_enabled=enrichment_enabled)
    handler.fail_next_expired.assert_awaited_once_with(**arguments)
    jobs.claim_next.assert_awaited_once_with(**arguments)
    handler.handle.assert_awaited_once_with(job=claimed_docx_job)


@pytest.mark.asyncio
@pytest.mark.parametrize("enrichment_enabled", [False, True])
async def test_empty_queue_returns_false(
    enrichment_enabled: bool,
    worker_harness: tuple[AsyncContainer, AsyncMock, AsyncMock],
) -> None:
    container, jobs, handler = worker_harness

    processed = await process_next_answer_key_enrichment_job(
        container=container,
        worker_id=WORKER_ID,
        now=DEFAULT_NOW,
        lease_ttl=LEASE_TTL,
        clock=FakeClock(now=DEFAULT_NOW),
        enrichment_enabled=enrichment_enabled,
    )

    assert processed is False
    arguments = expected_claim_arguments(enrichment_enabled=enrichment_enabled)
    handler.fail_next_expired.assert_awaited_once_with(**arguments)
    jobs.claim_next.assert_awaited_once_with(**arguments)
    handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("enrichment_enabled", [False, True])
async def test_expired_recovery_short_circuits_claim(
    enrichment_enabled: bool,
    worker_harness: tuple[AsyncContainer, AsyncMock, AsyncMock],
    claimed_docx_job: ExamAnswerKeyEnrichmentJob,
) -> None:
    container, jobs, handler = worker_harness
    handler.fail_next_expired.return_value = claimed_docx_job.model_copy(
        update={"status": ExamAnswerKeyEnrichmentJobStatus.FAILED, "source_docx": None}
    )

    processed = await process_next_answer_key_enrichment_job(
        container=container,
        worker_id=WORKER_ID,
        now=DEFAULT_NOW,
        lease_ttl=LEASE_TTL,
        clock=FakeClock(now=DEFAULT_NOW),
        enrichment_enabled=enrichment_enabled,
    )

    assert processed is True
    handler.fail_next_expired.assert_awaited_once_with(
        **expected_claim_arguments(enrichment_enabled=enrichment_enabled)
    )
    jobs.claim_next.assert_not_awaited()
    handler.handle.assert_not_awaited()
