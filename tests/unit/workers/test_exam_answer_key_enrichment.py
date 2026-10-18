from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide

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
from skriptoteket.workers import exam_answer_key_enrichment as enrichment_worker
from skriptoteket.workers.exam_answer_key_enrichment import process_next_answer_key_enrichment_job
from tests.unit.workers.execution_queue_repository_fakes import DEFAULT_NOW, FakeUow
from tests.unit.workers.execution_queue_runtime_fakes import FakeClock

WORKER_ID = "docx-worker"
LEASE_TTL = timedelta(seconds=30)


class AnswerKeyEnrichmentWorkerProvider(Provider):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        handler: ProcessExamAnswerKeyEnrichmentJobHandler,
    ) -> None:
        super().__init__()
        self._uow = uow
        self._jobs = jobs
        self._handler = handler

    @provide(scope=Scope.REQUEST)
    def uow(self) -> UnitOfWorkProtocol:
        return self._uow

    @provide(scope=Scope.REQUEST)
    def jobs(self) -> ExamAnswerKeyEnrichmentJobRepositoryProtocol:
        return self._jobs

    @provide(scope=Scope.REQUEST)
    def handler(self) -> ProcessExamAnswerKeyEnrichmentJobHandler:
        return self._handler


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
    container = make_async_container(
        AnswerKeyEnrichmentWorkerProvider(uow=FakeUow(), jobs=jobs, handler=handler)
    )
    return container, jobs, handler


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
    if enrichment_enabled:
        handler.fail_next_expired.assert_awaited_once_with(**arguments)
    else:
        assert [
            call.kwargs["source_kind"] for call in handler.fail_next_expired.await_args_list
        ] == [
            ExamAnswerKeySourceKind.DOCX_IMPORT,
            ExamAnswerKeySourceKind.DIGIEXAM_IMPORT,
        ]
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
    if enrichment_enabled:
        handler.fail_next_expired.assert_awaited_once_with(**arguments)
        jobs.claim_next.assert_awaited_once_with(**arguments)
    else:
        for boundary in (handler.fail_next_expired, jobs.claim_next):
            assert [call.kwargs["source_kind"] for call in boundary.await_args_list] == [
                ExamAnswerKeySourceKind.DOCX_IMPORT,
                ExamAnswerKeySourceKind.DIGIEXAM_IMPORT,
            ]
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_kind",
    [ExamAnswerKeySourceKind.DOCX_IMPORT, ExamAnswerKeySourceKind.WORKSPACE],
)
async def test_claimed_and_finished_events_name_the_job_kind(
    source_kind: ExamAnswerKeySourceKind,
    worker_harness: tuple[AsyncContainer, AsyncMock, AsyncMock],
    claimed_docx_job: ExamAnswerKeyEnrichmentJob,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container, jobs, handler = worker_harness
    job = claimed_docx_job
    if source_kind is ExamAnswerKeySourceKind.WORKSPACE:
        job = ExamAnswerKeyEnrichmentJob.model_validate(
            claimed_docx_job.model_dump()
            | {"source_kind": source_kind, "source_docx": None, "workspace_request_json": {}}
        )
    jobs.claim_next.return_value = job
    handler.handle.return_value = ExamAnswerKeyEnrichmentJob.model_validate(
        job.model_dump()
        | {"status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, "source_docx": None}
    )
    logger = Mock()
    monkeypatch.setattr(enrichment_worker, "logger", logger)

    await process_next_answer_key_enrichment_job(
        container=container,
        worker_id=WORKER_ID,
        now=DEFAULT_NOW,
        lease_ttl=LEASE_TTL,
        clock=FakeClock(now=DEFAULT_NOW),
    )

    events = {call.args[0]: call.kwargs for call in logger.info.call_args_list}
    assert events["Exam enrichment queue job claimed"] == {
        "job_id": str(job.id),
        "worker_id": WORKER_ID,
        "source_kind": source_kind.value,
    }
    assert events["Exam enrichment queue job finished"] == {
        "job_id": str(job.id),
        "status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED.value,
        "last_error": None,
        "source_kind": source_kind.value,
    }
