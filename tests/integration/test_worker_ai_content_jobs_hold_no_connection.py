"""Content-tag and editor-sent answer-key jobs release their connection before the provider call.

See ``worker_ai_connection_support`` for the harness and the invariant under test.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_content_tagging import ExamContentTagSuggester
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_attempts import (
    AnswerKeyAttemptLedger,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_workspace_lane import (  # noqa: E501
    ExamAnswerKeyEnrichmentWorkspaceLane,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    AnswerKeyProviderAttemptRunner,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.ai_route_connection_support import ConnectionProbe
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)
from tests.integration.worker_ai_connection_support import (
    PARALLEL_JOBS,
    GatedAnswerKeyProvider,
    GatedContentClassifier,
    ProviderGate,
    content_jobs,
    final_job,
    probe,
    run_gated,
    worker_engine,
    workspace_jobs,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import PROFILE

# The pytest fixtures live in the support module; naming them here registers them.
__all__ = ["probe", "worker_engine"]

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


@pytest.mark.parametrize("count", [1, PARALLEL_JOBS])
async def test_content_tag_jobs_hold_no_connection_during_classification(
    count: int,
    session_factory: async_sessionmaker[AsyncSession],
    worker_engine: AsyncEngine,
    probe: ConnectionProbe,
) -> None:
    owner = await create_owner(session_factory)
    jobs = await content_jobs(session_factory, owner, count)
    gate = ProviderGate(count)
    sessions = async_sessionmaker(worker_engine, expire_on_commit=False)

    async def process(job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        async with sessions() as session:
            return await ProcessExamContentSuggestionsHandler(
                classifier=ExamContentTagSuggester(
                    classifier=GatedContentClassifier(gate, session)
                ),
                jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
                users=PostgreSQLUserRepository(session),
                uow=SQLAlchemyUnitOfWork(session),
                clock=FixedClock(datetime.now(UTC)),
            ).handle(job=job)

    finished = await run_gated(
        jobs=jobs, probe=probe, engine=worker_engine, gate=gate, process=process
    )

    for job in finished:
        assert job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
        assert job.last_error == "ai_door_busy"
    for job in jobs:
        stored = await final_job(session_factory, job.id)
        assert stored.status == "failed" and stored.last_error == "ai_door_busy"


@pytest.mark.parametrize("count", [1, PARALLEL_JOBS])
async def test_workspace_suggestion_jobs_hold_no_connection_during_the_provider_call(
    count: int,
    session_factory: async_sessionmaker[AsyncSession],
    worker_engine: AsyncEngine,
    probe: ConnectionProbe,
) -> None:
    owner = await create_owner(session_factory)
    jobs = await workspace_jobs(session_factory, owner, count)
    gate = ProviderGate(count)
    sessions = async_sessionmaker(worker_engine, expire_on_commit=False)

    async def process(job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        clock = FixedClock(datetime.now(UTC))
        async with sessions() as session:
            jobs_repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
            uow = SQLAlchemyUnitOfWork(session)
            return await ExamAnswerKeyEnrichmentWorkspaceLane(
                enrichment_jobs=jobs_repository,
                users=PostgreSQLUserRepository(session),
                profile=PROFILE,
                uow=uow,
                clock=clock,
                ledger=AnswerKeyAttemptLedger(
                    enrichment_jobs=jobs_repository,
                    attempts=AnswerKeyProviderAttemptRunner(
                        provider=GatedAnswerKeyProvider(gate, session)
                    ),
                    uow=uow,
                    clock=clock,
                ),
            ).handle(job=job)

    finished = await run_gated(
        jobs=jobs, probe=probe, engine=worker_engine, gate=gate, process=process
    )

    for job in finished:
        assert job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
        assert job.last_error == "ai_door_busy"
