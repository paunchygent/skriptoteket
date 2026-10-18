"""Real PostgreSQL upload-to-published-document proof of the DOCX job over live recordings.

The production job handler, ``build_docx_conversion_pipeline`` composition, progress port, job
queue, token ledger, vault storage and QTI validators run unchanged. Only the network is
replaced: ``RecordedTransport`` (``exam_workspace_docx_background_support``) serves the live
replies recorded in
``tests/fixtures/exam_conversion/docx_key_provenance_v14/<exam>/`` to the real HTTP adapters.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    PLACEHOLDER_REASON,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.errors import DomainError
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
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
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
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_docx_background_support import (
    API_KEY,
    RecordedTransport,
    SavedRevisions,
    build_pipeline,
    document_store,
)
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
_LABEL_EXAM = "bf26_diagnostic_grammar_test_ht26_med_facit"


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
        OPENAI_LLM_ANSWER_KEY_API_KEY=API_KEY,
        LLM_DOCX_BATCH_FAMILIES=RECORDED_FAMILIES_PER_BATCH,
    )
    transport = RecordedTransport(RECORDINGS / _EXAM)
    batch_count = len(list((RECORDINGS / _EXAM).glob("docx_w*.json")))
    saved: list[tuple[str, int, int, int, int, int, int]] = []

    async with session_factory() as upload_session:
        queued = await ImportExamWorkspaceDocumentHandler(
            jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(upload_session),
            uow=SQLAlchemyUnitOfWork(upload_session),
            clock=clock,
            settings=settings,
            id_generator=ids,
        ).handle(actor=actor, filename=_QUIZ.name, content=_QUIZ.read_bytes(), course_key=None)
    assert queued.state == "queued"

    async def open_head() -> ExamWorkspaceDocumentResponse:
        async with session_factory() as reader:
            return await GetExamWorkspaceDocumentHandler(
                vault_files=PostgreSQLUserVaultFileRepository(reader),
                codec=ExamWorkspaceContainerCodec(),
                store=document_store(reader, storage=storage, clock=clock, settings=settings),
                jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(reader),
                uow=SQLAlchemyUnitOfWork(reader),
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
        store = document_store(session, storage=storage, clock=clock, settings=settings, uow=uow)
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
            pipeline = build_pipeline(
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
                progress=progress_port,
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
        assert model.diagnostics == list(finished.diagnostics)
        assert model.diagnostics
        assert all(event["stage"] == "formatting" for event in model.diagnostics)
        assert all(event["code"] in {"exact", "aligned", "rebuilt"} for event in model.diagnostics)
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
    formatting = [DocxBuildEvent.model_validate(event) for event in finished.diagnostics]
    assert Counter(event.anchors[0] for event in formatting) == Counter(
        item.source_anchor for item in document.items
    )
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
    transport = RecordedTransport(RECORDINGS / exam)
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
        course_key=None,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        pipeline = build_pipeline(
            client,
            settings=Settings.model_construct(
                LLM_ANSWER_KEY_ENABLED=True,
                OPENAI_LLM_ANSWER_KEY_API_KEY=API_KEY,
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


def _labeler_request(text: str) -> httpx.Request:
    """A second-pass item_type_label request carrying ``text`` as its rendered source."""
    return httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "text": {"format": {"name": "item_type_label", "strict": True}},
            "input": [{"content": [{"text": text}]}],
        },
    )


async def test_a_changed_labeler_request_has_no_recording() -> None:
    """A labeler prompt that differs from the recorded one is refused, not rebound to it."""
    exam_dir = RECORDINGS / _LABEL_EXAM
    stem = sorted(p.stem for p in exam_dir.glob("label_b_*.json"))[0]
    key = (exam_dir / f"{stem}.request.txt").read_text().removesuffix("\n")

    changed = RecordedTransport(exam_dir)
    assert (
        changed(_labeler_request(f"prefix\n\n### Question q1\n{key}\nPoäng: 1 poäng")).status_code
        == 500
    )
    assert changed.unmatched == ["no recording for item_type_label"]
    assert changed.served == []

    unchanged = RecordedTransport(exam_dir)
    assert unchanged(_labeler_request(f"prefix\n\n### Question q1\n{key}")).status_code == 200
    assert unchanged.served == [stem]
    assert unchanged.unmatched == []


async def test_a_recording_without_its_request_key_is_refused(tmp_path: Path) -> None:
    """A label_b recording with no capture-time key is refused, never matched by default."""
    source = RECORDINGS / _LABEL_EXAM
    copied = tmp_path / source.name
    shutil.copytree(source, copied)
    stem = sorted(p.stem for p in copied.glob("label_b_*.json"))[0]
    (copied / f"{stem}.request.txt").unlink()

    with pytest.raises(AssertionError, match=stem):
        RecordedTransport(copied)
