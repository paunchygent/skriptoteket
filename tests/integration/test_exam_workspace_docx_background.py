"""Real PostgreSQL upload-to-version-one proof replaying recorded live Responses rounds.

The two response fixtures are the output of a recorded live provider run on the quiz.
The HTTP adapter, job queue, token ledger, container storage and QTI validators
are the production implementations.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_token_lease import (
    ExamAnswerKeyTokenLeaseModel,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_token_leases import (
    PostgreSQLAnswerKeyTokenLeaseRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.test_exam_workspace_repositories import (
    _create_owner,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_answer_key_enrichment_jobs import _route

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_QUIZ = Path(
    "tests/fixtures/exam_conversion/docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx"
)
_RESPONSE = Path("tests/fixtures/exam_conversion/chapter_4_poetry_docx_build_response.json")
_RETRY = Path("tests/fixtures/exam_conversion/chapter_4_poetry_docx_build_retry_response.json")


async def test_quiz_background_job_commits_recorded_live_document_and_valid_qti(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    actor = await _create_owner(session_factory)
    now = datetime.now(UTC)
    clock = FixedClock(now)
    ids = SequenceIdGenerator([uuid4() for _ in range(5)])
    codec = ExamWorkspaceContainerCodec()
    storage = LocalVaultStorage(vault_root=tmp_path)
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000,
        VAULT_MAX_TOTAL_BYTES=50_000_000,
    )
    requests: list[dict[str, object]] = []

    def responses(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url.path == "/v1/responses"
        assert payload["text"]["format"]["strict"] is True
        assert payload["max_output_tokens"] == 16_384
        assert "tools" not in payload
        # Recorded live rounds: round 2 claims the one chunk round 1 left unclaimed.
        recorded = (_RESPONSE, _RETRY)[min(len(requests), 2) - 1]
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": recorded.read_text(encoding="utf-8")}
                        ],
                    }
                ],
            },
        )

    async with session_factory() as upload_session:
        importer = ImportExamWorkspaceDocumentHandler(
            jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(upload_session),
            uow=SQLAlchemyUnitOfWork(upload_session),
            clock=clock,
            settings=settings,
            id_generator=ids,
        )
        queued = await importer.handle(actor=actor, filename=_QUIZ.name, content=_QUIZ.read_bytes())
        assert queued.state == "queued" and requests == []

    async with session_factory() as session:
        jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        async with uow:
            running = await jobs.claim_next(
                worker_id="quiz-worker", now=now, lease_ttl=timedelta(minutes=15)
            )
        assert running is not None and running.id == queued.job_id
        vault_files = PostgreSQLUserVaultFileRepository(session)
        store = ExamWorkspaceDocumentStore(
            vault_files=vault_files,
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            vault_storage=storage,
            uow=uow,
            clock=clock,
            settings=settings,
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(responses)) as client:
            provider = OpenAIAnswerKeyStructuredProvider(
                client=client,
                base_url="https://example.test",
                api_key="fixture-key",
                timeout_seconds=30,
            )
            converter = DocxAIConverter(
                provider=provider,
                provider_selector=FixedRouteAnswerKeyProviderSelector(route=_route()),
                leases=PostgreSQLAnswerKeyTokenLeaseRepository(
                    session, daily_token_limit=1_000_000
                ),
                uow=uow,
                clock=clock,
                enabled=True,
            )
            processor = ProcessExamWorkspaceDocxJobHandler(
                jobs=jobs,
                chunker=PythonDocxExamChunker(),
                converter=converter,
                codec=codec,
                store=store,
                users=PostgreSQLUserRepository(session),
                uow=uow,
                clock=clock,
                id_generator=ids,
            )
            finished = await processor.handle(job=running)
        assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
        assert finished.source_docx is None and len(requests) == 2

    async with session_factory() as reader:
        model = await reader.get(ExamAnswerKeyEnrichmentJobModel, queued.job_id)
        assert model is not None and model.source_docx is None and model.status == "succeeded"
        assert [(e["round"], e["code"], e["anchors"]) for e in model.diagnostics] == [
            (1, "chunk_unclaimed", ["body:0003"])
        ]
        vault_files = PostgreSQLUserVaultFileRepository(reader)
        store = ExamWorkspaceDocumentStore(
            vault_files=vault_files,
            vault_usage=PostgreSQLUserVaultUsageRepository(reader),
            vault_storage=storage,
            uow=SQLAlchemyUnitOfWork(reader),
            clock=clock,
            settings=settings,
        )
        opened = await GetExamWorkspaceDocumentHandler(
            vault_files=vault_files, codec=codec, store=store
        ).handle(actor=actor, lineage_id=queued.lineage_id)
        document = opened.document
        assert opened.summary.version == 1
        assert len(document.items) == 28 and sum(item.points or 0 for item in document.items) == 28
        assert [item.kind.value for item in document.items] == ["single_choice"] * 21 + [
            "gap_fill"
        ] * 7
        assert all(item.answer_key.origin.value == "source_provided" for item in document.items)
        assert [item.answer_key.correct_choice_ids for item in document.items[:21]] == [
            (f"choice_{i:03d}",)
            for i in [1, 3, 2, 4, 2, 4, 3, 1, 1, 8, 2, 5, 6, 4, 3, 2, 1, 6, 3, 4, 7]
        ]
        assert [item.gaps[0].accepted_values for item in document.items[21:]] == [
            (word,)
            for word in [
                "cherish",
                "traverse",
                "humiliate",
                "out of the blue",
                "line",
                "diction",
                "alliteration",
            ]
        ]
        leases = (
            await reader.scalars(
                select(ExamAnswerKeyTokenLeaseModel).where(
                    ExamAnswerKeyTokenLeaseModel.job_id == queued.job_id
                )
            )
        ).all()
        assert len(leases) == 2 and all(lease.reserved_tokens > 16_384 for lease in leases)
        # The replayed bodies carry no usage, so no measured tokens are invented.
        assert all(lease.actual_tokens is None for lease in leases)
        package, report = build_native_examnet_qti_package(
            document, package_name="quiz", qti_writer=ExamNetQtiPackageWriter()
        )
        assert package.startswith(b"PK") and json.loads(report)["package_status"] == "passed"
