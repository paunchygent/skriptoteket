"""Real PostgreSQL upload-to-published-document proof of the DOCX job over live recordings.

The production job handler, ``build_docx_conversion_pipeline`` composition, progress port, job
queue, token ledger, vault storage and QTI validators run unchanged. Only the network is
replaced: an ``httpx.MockTransport`` serves the live replies recorded in
``tests/fixtures/exam_conversion/docx_build_v10/<exam>/`` to the real HTTP adapters.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    ConversionUnitState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    ExamWorkspaceConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    PLACEHOLDER_REASON,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionJob,
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_proposal_carry_forward import (
    CarryExamWorkspaceProposals,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    manifest_from_output,
    question_source,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
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
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_proposed_overlays import (
    PostgreSQLExamAnswerKeyProposedOverlayRepository,
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
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.docx_conversion_progress import ConversionOutline, ConversionUpdate
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    CORPUS,
    RECORDED_FAMILIES_PER_BATCH,
    RECORDINGS,
    GrantingLeases,
    NoSleep,
    NoTransaction,
    RecordingProgress,
    corpus_docx,
    recorded_exams,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_QUIZ = CORPUS / f"{_EXAM}.docx"
_KEY = "fixture-key"


def _anchors(node: JsonValue) -> set[str]:
    """Every source or answer-key anchor a recorded converter reply cites."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"source_anchors", "answer_key_anchors"} and isinstance(value, list):
                found.update(a for a in value if isinstance(a, str))
            else:
                found |= _anchors(value)
    elif isinstance(node, list):
        for value in node:
            found |= _anchors(value)
    return found


class RecordedTransport:
    """Serve each real HTTP request the recording the live run got for the same request."""

    def __init__(self, exam: str) -> None:
        self._dir = RECORDINGS / exam
        self._decisions = sorted(
            self._dir.glob("decisions_*.json"), key=lambda p: int(p.stem.rsplit("_", 1)[1])
        )
        self._batches = {p.stem: json.loads(p.read_text()) for p in self._dir.glob("docx_w*.json")}
        self._label_texts = self._label_b_source_texts(exam)
        self._groupings = 0
        self.served: list[str] = []
        self.unmatched: list[str] = []
        self.decisions_requests = 0
        self.responses_requests = 0

    def _label_b_source_texts(self, exam: str) -> dict[str, str]:
        """The second-pass source text of each recorded label_b question."""
        content = corpus_docx(exam)
        chunks = PythonDocxExamChunker().chunk(content=content)
        try:
            source = PythonDocxLabelerMarkdown().chunk(content=content)
        except ValueError:
            source = chunks
        manifest = manifest_from_output(
            json.loads((self._dir / "docx_grouping_1.json").read_text()), chunks
        )
        return {
            p.stem: question_source(manifest, source, p.stem.removeprefix("label_b_"))
            for p in self._dir.glob("label_b_*.json")
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {_KEY}"
        payload = json.loads(request.content)
        if request.url.path.endswith("/decisions"):
            self.decisions_requests += 1
            if len(self.served_decisions) >= len(self._decisions):
                return self._unmatched("more Decisions requests than recordings")
            path = self._decisions[len(self.served_decisions)]
            self.served.append(path.stem)
            return httpx.Response(200, json=json.loads(path.read_text()))
        assert request.url.path == "/v1/responses"
        self.responses_requests += 1
        assert payload["text"]["format"]["strict"] is True and "tools" not in payload
        name = self._resolve(payload)
        if name is None:
            return self._unmatched(f"no recording for {payload['text']['format']['name']}")
        self.served.append(name)
        body = (self._dir / f"{name}.json").read_text()
        output = [{"type": "message", "content": [{"type": "output_text", "text": body}]}]
        return httpx.Response(200, json={"status": "completed", "output": output})

    @property
    def served_decisions(self) -> list[str]:
        return [name for name in self.served if name.startswith("decisions_")]

    def _unmatched(self, why: str) -> httpx.Response:
        self.unmatched.append(why)
        return httpx.Response(500, json={"error": why})

    def _resolve(self, payload: Any) -> str | None:
        schema_name = payload["text"]["format"]["name"]
        text: str = payload["input"][0]["content"][0]["text"]
        if schema_name == "exam_source_manifest":
            self._groupings += 1
            return f"docx_grouping_{self._groupings}"
        if schema_name == "item_type_label":
            return next(
                (
                    n
                    for n, src in self._label_texts.items()
                    if n not in self.served and text.endswith(f"### Question q1\n{src}")
                ),
                None,
            )
        assert schema_name == "docx_exam_build"
        body = json.loads(text)
        pending = {c["anchor"] for c in body["chunks"]}
        visible = pending | {c["anchor"] for c in body["context_chunks"]}
        fits = {
            n: len(_anchors(r) & pending)
            for n, r in self._batches.items()
            if n not in self.served and _anchors(r) <= visible and _anchors(r) & pending
        }
        return max(sorted(fits), key=lambda n: fits[n], default=None)

    def all_recordings(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.json"))


class SavedRevisions(ExamWorkspaceConversionProgress):
    """The production progress port; after each save it reads the saved head back."""

    observe: Callable[[str, UUID], Awaitable[None]]  # set by the test before use

    async def outline(self, *, worker_id: str, job_id: UUID, outline: ConversionOutline) -> None:
        await super().outline(worker_id=worker_id, job_id=job_id, outline=outline)
        await self.observe("outline", job_id)

    async def batch_ready(self, *, worker_id: str, job_id: UUID, update: ConversionUpdate) -> None:
        await super().batch_ready(worker_id=worker_id, job_id=job_id, update=update)
        await self.observe("batch_ready", job_id)


def _pipeline(
    client: httpx.AsyncClient,
    *,
    settings: Settings,
    leases: Any,
    uow: Any,
    clock: FixedClock,
    progress: Any,
    sleeper: Any,
) -> DocxConversionPipeline:
    """The production composition over real Responses and Decisions adapters."""
    return build_docx_conversion_pipeline(
        client=client,
        provider=OpenAIAnswerKeyStructuredProvider(
            client=client,
            base_url=settings.LLM_ANSWER_KEY_BASE_URL,
            api_key=_KEY,
            timeout_seconds=30,
        ),
        sleeper=sleeper,
        leases=leases,
        uow=SerializedUnitOfWork(uow),
        clock=clock,
        settings=settings,
        progress=progress,
    )


def _document_store(
    session: AsyncSession,
    *,
    storage: LocalVaultStorage,
    clock: FixedClock,
    settings: Settings,
    uow: SQLAlchemyUnitOfWork | None = None,
) -> ExamWorkspaceDocumentStore:
    return ExamWorkspaceDocumentStore(
        vault_files=PostgreSQLUserVaultFileRepository(session),
        vault_usage=PostgreSQLUserVaultUsageRepository(session),
        vault_storage=storage,
        uow=uow or SQLAlchemyUnitOfWork(session),
        clock=clock,
        settings=settings,
        proposal_carry_forward=CarryExamWorkspaceProposals(
            enrichment_jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            proposed_overlays=PostgreSQLExamAnswerKeyProposedOverlayRepository(session),
            clock=clock,
            id_generator=UUID4Generator(),
        ),
    )


async def test_quiz_job_saves_batches_progressively_and_publishes_complete_document(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    clock = FixedClock(now)
    ids = UUID4Generator()
    storage = LocalVaultStorage(vault_root=tmp_path)
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000,
        VAULT_MAX_TOTAL_BYTES=50_000_000,
        LLM_ANSWER_KEY_ENABLED=True,
        OPENAI_LLM_ANSWER_KEY_API_KEY=_KEY,
        LLM_DOCX_BATCH_FAMILIES=RECORDED_FAMILIES_PER_BATCH,
    )
    transport = RecordedTransport(_EXAM)
    batch_count = len(list((RECORDINGS / _EXAM).glob("docx_w*.json")))
    saved: list[tuple[str, int, int, int, int, int, int]] = []

    async with session_factory() as upload_session:
        queued = await ImportExamWorkspaceDocumentHandler(
            jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(upload_session),
            uow=SQLAlchemyUnitOfWork(upload_session),
            clock=clock,
            settings=settings,
            id_generator=ids,
        ).handle(actor=actor, filename=_QUIZ.name, content=_QUIZ.read_bytes())
    assert queued.state == "queued"

    async def open_head() -> ExamWorkspaceDocumentResponse:
        async with session_factory() as reader:
            return await GetExamWorkspaceDocumentHandler(
                vault_files=PostgreSQLUserVaultFileRepository(reader),
                codec=ExamWorkspaceContainerCodec(),
                store=_document_store(reader, storage=storage, clock=clock, settings=settings),
            ).handle(actor=actor, lineage_id=queued.lineage_id)

    async def observe(call: str, job_id: UUID) -> None:
        async with session_factory() as reader:
            row = await reader.get(ExamAnswerKeyEnrichmentJobModel, job_id)
        assert row is not None and row.conversion_progress is not None
        progress = ConversionProgress.model_validate(row.conversion_progress)
        try:
            head = await open_head()
        except DomainError:
            assert call == "outline", "A batch save must leave a saved document behind."
            return
        saved.append(
            (
                call,
                head.document.revision,
                head.summary.version,
                progress.questions_done,
                progress.questions_total - progress.questions_done,
                len(head.document.items),
                sum(PLACEHOLDER_REASON in i.review.reasons for i in head.document.items),
            )
        )

    async with session_factory() as session:
        jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        async with uow:
            running = await jobs.claim_next(
                worker_id="quiz-worker", now=now, lease_ttl=timedelta(minutes=15)
            )
        assert running is not None and running.id == queued.job_id
        store = _document_store(session, storage=storage, clock=clock, settings=settings, uow=uow)
        progress_port = SavedRevisions(
            jobs=jobs,
            users=PostgreSQLUserRepository(session),
            vault_files=PostgreSQLUserVaultFileRepository(session),
            store=store,
            codec=ExamWorkspaceContainerCodec(),
            uow=uow,
            clock=clock,
            id_generator=ids,
        )
        progress_port.observe = observe
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            pipeline = _pipeline(
                client,
                settings=settings,
                leases=PostgreSQLAnswerKeyTokenLeaseRepository(
                    session, daily_token_limit=50_000_000
                ),
                uow=uow,
                clock=clock,
                progress=progress_port,
                sleeper=AsyncioSleeper(),
            )
            finished = await ProcessExamWorkspaceDocxJobHandler(
                jobs=jobs,
                chunker=PythonDocxExamChunker(),
                pipeline=pipeline,
                progress=progress_port,  # type: ignore[arg-type]
                store=store,
                users=PostgreSQLUserRepository(session),
                uow=uow,
                clock=clock,
                id_generator=ids,
            ).handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, finished.diagnostics
    assert transport.unmatched == []
    assert sorted(transport.served) == transport.all_recordings()
    assert finished.source_docx is None

    # D30: the document is saved when the first batch is ready, placeholders for the rest.
    assert len(saved) == batch_count, saved
    assert all(call == "batch_ready" for call, *_ in saved)
    revisions = [revision for _, revision, *_ in saved]
    assert revisions == sorted(set(revisions)) and revisions[0] == 1
    first, last = saved[0], saved[-1]
    assert first[4] > 0 and first[6] == first[4], f"first save must hold placeholders: {first}"
    assert [s[3] for s in saved] == sorted(s[3] for s in saved)
    assert [s[4] for s in saved] == sorted((s[4] for s in saved), reverse=True)
    assert last[4] == 0 and last[6] == 0 and last[3] == first[3] + first[4]
    assert all(s[3] + s[4] == first[3] + first[4] for s in saved)

    async with session_factory() as reader:
        model = await reader.get(ExamAnswerKeyEnrichmentJobModel, queued.job_id)
        assert model is not None and model.source_docx is None and model.status == "succeeded"
        assert model.diagnostics == []
        stored = ConversionProgress.model_validate(model.conversion_progress)
        assert stored.questions_done == stored.questions_total == first[3] + first[4]
        assert all(u.state is ConversionUnitState.READY for u in stored.units if u.question)
        versions = (
            await reader.scalars(
                select(UserVaultFileModel).where(
                    UserVaultFileModel.document_lineage_id == queued.lineage_id
                )
            )
        ).all()
        live = [v for v in versions if v.deleted_at is None]
        assert [v.document_version for v in live] == [stored.revision]
        assert stored.revision == max(v.document_version or 0 for v in versions)

        leases = (
            await reader.scalars(
                select(ExamAnswerKeyTokenLeaseModel).where(
                    ExamAnswerKeyTokenLeaseModel.job_id == queued.job_id
                )
            )
        ).all()
        # One lease per provider call: every Responses call and every Decisions request.
        assert len(leases) == transport.responses_requests + transport.decisions_requests
        assert all(lease.reserved_tokens > 0 for lease in leases)
        # Recorded Decisions replies carry usage, so those reservations are reconciled;
        # recorded Responses replies carry none, so no measured tokens are invented.
        reconciled = [lease for lease in leases if lease.actual_tokens is not None]
        assert len(reconciled) == transport.decisions_requests
        assert all(lease.reserved_tokens > (lease.actual_tokens or 0) for lease in reconciled)

    opened = await open_head()
    document = opened.document
    assert opened.summary.version == stored.revision == document.revision
    assert opened.notes  # recorded facit chunks survive as teacher notes
    assert not [i for i in document.items if PLACEHOLDER_REASON in i.review.reasons]
    assert all(i.answer_key.origin.value == "source_provided" for i in document.items)
    package, report = build_native_examnet_qti_package(
        document, package_name="quiz", qti_writer=ExamNetQtiPackageWriter()
    )
    assert package.startswith(b"PK") and json.loads(report)["package_status"] == "passed"


@pytest.mark.parametrize("exam", recorded_exams())
async def test_every_recording_is_served_once_to_its_own_request(exam: str) -> None:
    """The HTTP-level request keying matches each live recording exactly once, in every exam."""
    transport = RecordedTransport(exam)
    progress = RecordingProgress()
    content = corpus_docx(exam)
    job = DocxConversionJob(
        job_id=uuid4(),
        worker_id="replay-worker",
        document_id=uuid4(),
        filename=f"{exam}.docx",
        source_sha256=hashlib.sha256(content).hexdigest(),
        source_docx=content,
        chunks=PythonDocxExamChunker().chunk(content=content),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        pipeline = _pipeline(
            client,
            settings=Settings.model_construct(
                LLM_ANSWER_KEY_ENABLED=True,
                OPENAI_LLM_ANSWER_KEY_API_KEY=_KEY,
                LLM_DOCX_BATCH_FAMILIES=RECORDED_FAMILIES_PER_BATCH,
            ),
            leases=GrantingLeases(),
            uow=NoTransaction(),
            clock=FixedClock(datetime(2026, 10, 11, tzinfo=UTC)),
            progress=progress,
            sleeper=NoSleep(),
        )
        outcome = await pipeline.convert(job=job)
    assert transport.unmatched == []
    assert sorted(transport.served) == transport.all_recordings()
    assert not [i for i in outcome.result.document.items if PLACEHOLDER_REASON in i.review.reasons]
