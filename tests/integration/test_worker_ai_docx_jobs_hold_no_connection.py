"""DOCX jobs release their connection before the provider call.

See ``worker_ai_connection_support`` for the harness and the invariant under test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    ExamWorkspaceConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.payload_guard_fixtures import unpooled_payload_guard_engine
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.ai_route_connection_support import ConnectionProbe
from tests.integration.exam_workspace_docx_background_support import (
    RecordedTransport,
    build_pipeline,
    document_store,
)
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)
from tests.integration.worker_ai_connection_support import (
    EXAM,
    PARALLEL_JOBS,
    GatedDocxPipeline,
    GatedRecordedTransport,
    ProviderGate,
    docx_jobs,
    import_settings,
    probe,
    run_gated,
    worker_engine,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
)

# The pytest fixtures live in the support module; naming them here registers them.
__all__ = ["probe", "worker_engine"]

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


@pytest.mark.parametrize("count", [1, PARALLEL_JOBS])
async def test_docx_jobs_hold_no_connection_during_grouping(
    count: int,
    session_factory: async_sessionmaker[AsyncSession],
    worker_engine: AsyncEngine,
    probe: ConnectionProbe,
    tmp_path: Path,
) -> None:
    owner = await create_owner(session_factory)
    jobs = await docx_jobs(session_factory, owner, count)
    gate = ProviderGate(count)
    sessions = async_sessionmaker(worker_engine, expire_on_commit=False)
    settings = import_settings()

    async def process(job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        clock = FixedClock(datetime.now(UTC))
        ids = UUID4Generator()
        async with sessions() as session:
            uow = SQLAlchemyUnitOfWork(session)
            store = document_store(
                session,
                storage=LocalVaultStorage(vault_root=tmp_path),
                clock=clock,
                settings=settings,
                uow=uow,
            )
            users = PostgreSQLUserRepository(session)
            jobs_repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
            return await ProcessExamWorkspaceDocxJobHandler(
                jobs=jobs_repository,
                chunker=PythonDocxExamChunker(),
                pipeline=GatedDocxPipeline(gate, session),
                progress=ExamWorkspaceConversionProgress(
                    jobs=jobs_repository,
                    users=users,
                    vault_files=PostgreSQLUserVaultFileRepository(
                        session, unpooled_payload_guard_engine(session.bind)
                    ),
                    store=store,
                    codec=ExamWorkspaceContainerCodec(),
                    uow=uow,
                    clock=clock,
                    id_generator=ids,
                ),
                store=store,
                users=users,
                uow=uow,
                clock=clock,
                id_generator=ids,
            ).handle(job=job)

    finished = await run_gated(
        jobs=jobs, probe=probe, engine=worker_engine, gate=gate, process=process
    )

    for job in finished:
        assert job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED, job.diagnostics
        assert job.diagnostics[-1]["code"] == "ai_door_busy"


async def test_real_docx_pipeline_holds_no_connection_during_its_grouping_call(
    session_factory: async_sessionmaker[AsyncSession],
    worker_engine: AsyncEngine,
    probe: ConnectionProbe,
    tmp_path: Path,
) -> None:
    """The production pipeline, progress port and door client run to a published document."""
    owner = await create_owner(session_factory)
    (job,) = await docx_jobs(session_factory, owner, 1)
    gate = ProviderGate(1)
    settings = import_settings()
    clock = FixedClock(datetime.now(UTC))
    ids = UUID4Generator()
    transport = RecordedTransport(RECORDINGS / EXAM)
    sessions = async_sessionmaker(worker_engine, expire_on_commit=False)

    async def process() -> ExamAnswerKeyEnrichmentJob:
        async with sessions() as session:
            uow = SQLAlchemyUnitOfWork(session)
            store = document_store(
                session,
                storage=LocalVaultStorage(vault_root=tmp_path),
                clock=clock,
                settings=settings,
                uow=uow,
            )
            users = PostgreSQLUserRepository(session)
            jobs_repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
            progress = ExamWorkspaceConversionProgress(
                jobs=jobs_repository,
                users=users,
                vault_files=PostgreSQLUserVaultFileRepository(
                    session, unpooled_payload_guard_engine(session.bind)
                ),
                store=store,
                codec=ExamWorkspaceContainerCodec(),
                uow=uow,
                clock=clock,
                id_generator=ids,
            )
            gated = GatedRecordedTransport(transport, gate, session)
            async with httpx.AsyncClient(transport=httpx.MockTransport(gated)) as client:
                return await ProcessExamWorkspaceDocxJobHandler(
                    jobs=jobs_repository,
                    chunker=PythonDocxExamChunker(),
                    pipeline=build_pipeline(
                        client,
                        settings=settings,
                        uow=uow,
                        progress=progress,
                        sleeper=AsyncioSleeper(),
                    ),
                    progress=progress,
                    store=store,
                    users=users,
                    uow=uow,
                    clock=clock,
                    id_generator=ids,
                ).handle(job=job)

    (finished,) = await run_gated(
        jobs=[job], probe=probe, engine=worker_engine, gate=gate, process=lambda _job: process()
    )

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, finished.diagnostics
    assert transport.unmatched == []
