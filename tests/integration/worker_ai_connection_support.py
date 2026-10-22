"""Worker AI jobs release their database connection before the provider call runs.

TASK-SKRIPT-41-01-04 review finding F2. The worker runs eight jobs at once on one pool of
eight connections. A job that keeps a connection checked out while it awaits a provider
caps the number of concurrent AI calls and starves the worker's own claim and heartbeat
transactions. These tests run the production DOCX and content-tag job handlers over real
repositories and a real PostgreSQL pool of two connections, with a gated fake at the provider
seam. While every job waits at the gate, the tests assert that:

- no job's session is in a transaction,
- the application pool has no connection checked out and the database has no session idle in
  a transaction, and
- a separate worker operation (the claim and heartbeat stand-in) still gets a connection.

The pool of two makes a held connection visible even when only a few jobs run: a job that
holds one starves the others, so they never reach the gate.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionOutcome,
    DocxConversionPipelineProtocol,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_item_views,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import AiDoorBusy, AiDoorCaller
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassification,
    ContentTagClassificationRequest,
)
from tests.fixtures.docx_corpus import CORPUS
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.ai_route_connection_support import ConnectionProbe
from tests.integration.exam_workspace_docx_background_support import (
    RecordedTransport,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDED_FAMILIES_PER_BATCH,
)
from tests.unit.application.curated_apps.handlers.workspace_enrichment_job_support import (
    unkeyed_choice_document,
)
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    suggestion_document,
    suggestion_item,
)

EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_QUIZ = CORPUS / f"{EXAM}.docx"
_COURSE = ExamCourseChoice(key="ADMADM01", name="Administration 1")
PARALLEL_JOBS = 8
_POOL_SIZE = 2
_BOUNDARY_TIMEOUT_SECONDS = 6.0
_HEARTBEAT_TIMEOUT_SECONDS = 2.0


class ProviderGate:
    """Holds every job at its provider call until the test releases them."""

    def __init__(self, expected: int) -> None:
        self._expected = expected
        self.entered = 0
        self.open_transactions: list[bool] = []
        self.all_entered = asyncio.Event()
        self.release = asyncio.Event()

    async def hold(self, session: AsyncSession) -> None:
        self.entered += 1
        self.open_transactions.append(session.in_transaction())
        if self.entered == self._expected:
            self.all_entered.set()
        await self.release.wait()


class GatedDocxPipeline(DocxConversionPipelineProtocol):
    """Reaches the grouping boundary, holds there, then reports a busy door."""

    def __init__(self, gate: ProviderGate, session: AsyncSession) -> None:
        self._gate = gate
        self._session = session

    async def convert(
        self, *, job: DocxConversionJob, fallback_reason: str | None = None
    ) -> DocxConversionOutcome:
        await self._gate.hold(self._session)
        raise AiDoorBusy(retry_after_seconds=None)


class GatedContentClassifier:
    """The content classifier seam: holds at the provider call, then reports a busy door."""

    def __init__(self, gate: ProviderGate, session: AsyncSession) -> None:
        self._gate = gate
        self._session = session

    @property
    def provider_profile_id(self) -> str:
        return "gated"

    def estimate_content_tokens(self, *, request: ContentTagClassificationRequest) -> int:
        return 1

    async def classify_content(
        self, *, request: ContentTagClassificationRequest
    ) -> ContentTagClassification:
        await self._gate.hold(self._session)
        raise AiDoorBusy(retry_after_seconds=None)


class GatedAnswerKeyProvider(AnswerKeyStructuredProviderProtocol):
    """The answer-key provider seam: holds at the call, then reports a busy door."""

    def __init__(self, gate: ProviderGate, session: AsyncSession) -> None:
        self._gate = gate
        self._session = session

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> StructuredLLMResponse:
        await self._gate.hold(self._session)
        raise AiDoorBusy(retry_after_seconds=None)


class GatedRecordedTransport:
    """Serves the recorded replies and holds the first request: the grouping call."""

    def __init__(self, recorded: RecordedTransport, gate: ProviderGate, session: AsyncSession):
        self._recorded = recorded
        self._gate = gate
        self._session = session
        self._held = False

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        if not self._held:
            self._held = True
            await self._gate.hold(self._session)
        return self._recorded(request)


@pytest.fixture
async def worker_engine(migrated_db: str) -> AsyncIterator[AsyncEngine]:
    """The worker's pool, small enough that one held connection starves the next job."""
    engine = create_async_engine(
        migrated_db, pool_size=_POOL_SIZE, max_overflow=0, pool_timeout=30, pool_pre_ping=True
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def probe(migrated_db: str, worker_engine: AsyncEngine) -> AsyncIterator[ConnectionProbe]:
    observer = create_async_engine(migrated_db, poolclass=NullPool)
    connection_probe = ConnectionProbe()
    connection_probe.bind(engine=worker_engine, observer=observer)
    yield connection_probe
    await observer.dispose()


async def content_jobs(
    session_factory: async_sessionmaker[AsyncSession], owner: User, count: int
) -> list[ExamAnswerKeyEnrichmentJob]:
    """Running content-tag jobs, each claimed by its own worker slot."""
    now = datetime.now(UTC)
    jobs: list[ExamAnswerKeyEnrichmentJob] = []
    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        for slot in range(count):
            lineage_id = uuid4()
            draft = suggestion_document(lineage_id, suggestion_item(item_id="item_001", sequence=1))
            saved = draft.model_copy(
                update={"header": draft.header.model_copy(update={"course": _COURSE})}
            )
            jobs.append(
                await repository.create(
                    job=ExamAnswerKeyEnrichmentJob(
                        id=uuid4(),
                        source_kind=ExamAnswerKeySourceKind.CONTENT_TAGS,
                        owner_user_id=owner.id,
                        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
                        input_filename=saved.title,
                        workspace_lineage_id=lineage_id,
                        workspace_document_revision=saved.revision,
                        workspace_course_key=_COURSE.key,
                        workspace_request_json=saved.model_dump(mode="json"),
                        attempts=1,
                        available_at=now,
                        locked_by=f"content-worker:{slot}",
                        locked_until=now + timedelta(minutes=15),
                        created_at=now,
                        updated_at=now,
                        started_at=now,
                    )
                )
            )
    return jobs


async def workspace_jobs(
    session_factory: async_sessionmaker[AsyncSession], owner: User, count: int
) -> list[ExamAnswerKeyEnrichmentJob]:
    """Running editor-sent answer-key suggestion jobs, each claimed by its own worker slot."""
    now = datetime.now(UTC)
    async with session_factory() as session:
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        queued_ids: set[UUID] = set()
        async with uow:
            for _ in range(count):
                document = unkeyed_choice_document(document_id=uuid4())
                created = await repository.create(
                    job=enqueue_workspace_enrichment_job(
                        job_id=uuid4(),
                        owner_user_id=owner.id,
                        input_filename=document.title,
                        workspace_lineage_id=document.document_id,
                        workspace_document_revision=document.revision,
                        workspace_request_json=WorkspaceAnswerKeyRequestPayload(
                            views=answer_key_item_views(document)
                        ).model_dump(mode="json"),
                        now=now,
                    )
                )
                queued_ids.add(created.id)
        claimed: list[ExamAnswerKeyEnrichmentJob] = []
        for slot in range(count):
            async with uow:
                job = await repository.claim_next(
                    worker_id=f"workspace-worker:{slot}",
                    now=now,
                    lease_ttl=timedelta(minutes=15),
                    source_kind=ExamAnswerKeySourceKind.WORKSPACE,
                )
            assert job is not None and job.id in queued_ids
            claimed.append(job)
    return claimed


def import_settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000,
        VAULT_MAX_TOTAL_BYTES=50_000_000,
        LLM_ANSWER_KEY_ENABLED=True,
        LLM_DOCX_BATCH_FAMILIES=RECORDED_FAMILIES_PER_BATCH,
    )


async def docx_jobs(
    session_factory: async_sessionmaker[AsyncSession], owner: User, count: int
) -> list[ExamAnswerKeyEnrichmentJob]:
    """Running DOCX jobs, each imported through the production handler and claimed."""
    now = datetime.now(UTC)
    queued_ids: set[UUID] = set()
    for _ in range(count):
        async with session_factory() as session:
            queued = await ImportExamWorkspaceDocumentHandler(
                jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
                uow=SQLAlchemyUnitOfWork(session),
                clock=FixedClock(now),
                settings=import_settings(),
                id_generator=UUID4Generator(),
            ).handle(actor=owner, filename=_QUIZ.name, content=_QUIZ.read_bytes(), course_key=None)
        queued_ids.add(queued.job_id)
    claimed: list[ExamAnswerKeyEnrichmentJob] = []
    async with session_factory() as session:
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        for slot in range(count):
            async with uow:
                job = await repository.claim_next(
                    worker_id=f"docx-worker:{slot}",
                    now=now,
                    lease_ttl=timedelta(minutes=15),
                    source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
                )
            assert job is not None and job.id in queued_ids
            claimed.append(job)
    return claimed


async def final_job(
    session_factory: async_sessionmaker[AsyncSession], job_id: UUID
) -> ExamAnswerKeyEnrichmentJobModel:
    async with session_factory() as session:
        row = await session.get(ExamAnswerKeyEnrichmentJobModel, job_id)
    assert row is not None
    return row


async def _assert_no_connection_held_at_the_gate(
    *,
    gate: ProviderGate,
    probe: ConnectionProbe,
    engine: AsyncEngine,
    tasks: list[asyncio.Task[ExamAnswerKeyEnrichmentJob]],
    expected: int,
) -> None:
    """While every job waits at its provider: no held connection, and a heartbeat gets one."""
    try:
        await asyncio.wait_for(gate.all_entered.wait(), timeout=_BOUNDARY_TIMEOUT_SECONDS)
    except TimeoutError:
        crashed = [task.exception() for task in tasks if task.done() and not task.cancelled()]
        pytest.fail(
            f"Only {gate.entered} of {expected} jobs reached their provider call: the others "
            f"waited for a pooled connection that earlier jobs held "
            f"(open transactions {gate.open_transactions}, crashed jobs {crashed})."
        )
    await probe.sample("all jobs at their provider call")
    assert gate.open_transactions == [False] * expected, gate.open_transactions
    assert probe.held_during_calls() == [0], probe.samples

    async def heartbeat() -> None:
        async with async_sessionmaker(engine)() as session, session.begin():
            await session.execute(text("SELECT 1"))

    await asyncio.wait_for(heartbeat(), timeout=_HEARTBEAT_TIMEOUT_SECONDS)
    assert not any(task.done() for task in tasks)


async def _release_and_finish(
    gate: ProviderGate, tasks: list[asyncio.Task[ExamAnswerKeyEnrichmentJob]]
) -> list[ExamAnswerKeyEnrichmentJob]:
    gate.release.set()
    return list(await asyncio.gather(*tasks))


async def run_gated(
    *,
    jobs: list[ExamAnswerKeyEnrichmentJob],
    probe: ConnectionProbe,
    engine: AsyncEngine,
    gate: ProviderGate,
    process: Callable[
        [ExamAnswerKeyEnrichmentJob], Coroutine[object, object, ExamAnswerKeyEnrichmentJob]
    ],
) -> list[ExamAnswerKeyEnrichmentJob]:
    tasks = [asyncio.create_task(process(job)) for job in jobs]
    try:
        await _assert_no_connection_held_at_the_gate(
            gate=gate, probe=probe, engine=engine, tasks=tasks, expected=len(jobs)
        )
        return await _release_and_finish(gate, tasks)
    finally:
        gate.release.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
