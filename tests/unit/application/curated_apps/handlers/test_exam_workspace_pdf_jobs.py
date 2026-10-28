"""A Word-saved PDF runs the existing Word conversion job and opens as version one."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    is_answer_line_chunk,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_import_source import (  # noqa: E501
    ImportSourceChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    NO_READABLE_TEXT,
    PdfPlumberExamChunker,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.docx_corpus import corpus_docx
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    InMemoryEnrichmentJobRepository,
    replayed_docx_job_handler,
)
from tests.unit.application.curated_apps.handlers.docx_door_limit_support import (
    DoorScript,
    exam_bytes,
    grouping_for,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    NoSleep,
    NoTransaction,
    Replay,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _Env,
    _settings,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import (
    merged,
    pdf_bytes,
)

PDF_CORPUS = Path(
    "tests/fixtures/exam_conversion/pdf_corpus/bf26_english_1_unit_test_kap_1_2_med_facit.pdf"
)


class PdfJobEnvironment(_Env):
    jobs: InMemoryEnrichmentJobRepository
    actor: User
    replay: Replay
    importer: ImportExamWorkspaceDocumentHandler
    processor: ProcessExamWorkspaceDocxJobHandler


def pdf_environment() -> PdfJobEnvironment:
    """The DOCX job with the production dispatch chunker and AI disabled."""
    env = PdfJobEnvironment()
    env.jobs = InMemoryEnrichmentJobRepository()
    env.actor = _actor()
    env.importer = ImportExamWorkspaceDocumentHandler(
        jobs=env.jobs,
        uow=env.store._uow,
        clock=FixedClock(_NOW),
        settings=_settings(),
        id_generator=env.ids,
    )
    env.processor, env.replay = replayed_docx_job_handler(
        enrichment_jobs=env.jobs,
        vault_files=env.vault_files,
        vault_storage=env.vault_storage,
        codec=env.codec,
        exam="chapter_4_poetry_and_lyrics_quiz_med_facit",
        store=env.store,
        users=AsyncMock(get_by_id=AsyncMock(return_value=env.actor)),
        enabled=False,
        chunker=ImportSourceChunker(docx=PythonDocxExamChunker(), pdf=PdfPlumberExamChunker()),
    )
    return env


async def pdf_claim(env: PdfJobEnvironment) -> ExamAnswerKeyEnrichmentJob:
    content = PDF_CORPUS.read_bytes()
    status = await env.importer.handle(
        actor=env.actor, filename="prov.pdf", content=content, course_key=None
    )
    assert status.state == "queued"
    assert env.replay.provider.requests == []
    assert not env.vault_files.files
    queued = env.jobs.jobs[status.job_id]
    running = queued.model_copy(
        update={
            "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
            "locked_by": "worker",
            "locked_until": _NOW + timedelta(minutes=10),
        }
    )
    env.jobs.jobs[running.id] = running
    return running


async def _claim(
    env: PdfJobEnvironment, *, filename: str, content: bytes
) -> ExamAnswerKeyEnrichmentJob:
    status = await env.importer.handle(
        actor=env.actor, filename=filename, content=content, course_key=None
    )
    assert status.state == "queued"
    queued = env.jobs.jobs[status.job_id]
    running = queued.model_copy(
        update={
            "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
            "locked_by": "worker",
            "locked_until": _NOW + timedelta(minutes=10),
        }
    )
    env.jobs.jobs[running.id] = running
    return running


async def _open_finished(env: PdfJobEnvironment, running: ExamAnswerKeyEnrichmentJob):
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_docx is None
    assert running.workspace_lineage_id is not None
    return await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)


def page_exam_pdf() -> bytes:
    """A three-question exam PDF whose second page is blank, so page 3 is unreadable."""
    return merged(
        pdf_bytes("<p>Prov i svenska</p>"),
        pdf_bytes("<p>1. Vad heter huvudpersonen?</p>"),
        pdf_bytes("<p></p>"),
        pdf_bytes("<p>2. Vilken färg har båten?</p>"),
    )


SKIPPED_PAGE_NOTE = "Sida 3 importerades inte eftersom texten inte gick att läsa in."


def scripted_processor(
    env: PdfJobEnvironment, script: DoorScript
) -> ProcessExamWorkspaceDocxJobHandler:
    """The PDF job handler over a scripted door, so batches publish and a later call can fail."""
    pipeline = build_docx_conversion_pipeline(
        door=script.door,
        provider=OpenAIAnswerKeyStructuredProvider(door=script.door, timeout_seconds=5.0),
        sleeper=NoSleep(),
        uow=SerializedUnitOfWork(NoTransaction()),
        settings=Settings.model_construct(
            LLM_ANSWER_KEY_ENABLED=True,
            LLM_DOCX_BATCH_FAMILIES=1,
            LLM_ITEM_LABELER_TIMEOUT_SECONDS=5,
            LLM_DOCX_CONVERSION_TIMEOUT_SECONDS=5,
        ),
        progress=env.replay.progress,
    )
    return ProcessExamWorkspaceDocxJobHandler(
        jobs=env.jobs,
        chunker=ImportSourceChunker(docx=PythonDocxExamChunker(), pdf=PdfPlumberExamChunker()),
        pipeline=pipeline,
        progress=env.replay.progress,
        store=env.store,
        users=AsyncMock(get_by_id=AsyncMock(return_value=env.actor)),
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        id_generator=env.ids,
    )


def script_for(content: bytes, *, refuse_batch_calls: tuple[int, ...] = ()) -> DoorScript:
    """One answer per question for ``content``'s chunks, refusing the named batch calls."""
    anchors = [chunk.anchor for chunk in PdfPlumberExamChunker().chunk(content=content).chunks]
    return DoorScript(grouping=grouping_for(anchors), refuse_batch_calls=refuse_batch_calls)


@pytest.mark.asyncio
async def test_a_failed_pdf_import_keeps_the_skipped_page_note_with_its_batches():
    """F1: the retained partial exam names its skipped page, as D2 requires."""
    env = pdf_environment()
    content = page_exam_pdf()
    processor = scripted_processor(env, script_for(content, refuse_batch_calls=(2,)))
    running = await _claim(env, filename="prov-med-tom-sida.pdf", content=content)

    finished = await processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.source_docx is None
    assert env.replay.progress.calls[0] == "outline"
    assert "batch_ready" in env.replay.progress.calls, "the readable batch stays saved"
    assert env.replay.progress.calls[-1] == "abandon"
    assert env.replay.progress.finals == [], "the refused conversion publishes no final document"
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    assert opened.notes == (SKIPPED_PAGE_NOTE,)


@pytest.mark.asyncio
async def test_a_completed_pdf_import_names_its_skipped_page_once_with_or_without_batches():
    env = pdf_environment()
    content = page_exam_pdf()
    processor = scripted_processor(env, script_for(content))
    running = await _claim(env, filename="prov-med-tom-sida.pdf", content=content)

    finished = await processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert set(env.replay.progress.notes) == {(SKIPPED_PAGE_NOTE,)}
    assert len(env.replay.progress.notes) >= 2, "the batches publish before the final save"
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    assert opened.notes == (SKIPPED_PAGE_NOTE,)


@pytest.mark.asyncio
async def test_word_batches_carry_no_import_notes():
    env = pdf_environment()
    content = exam_bytes()
    anchors = [chunk.anchor for chunk in PythonDocxExamChunker().chunk(content=content).chunks]
    script = DoorScript(grouping=grouping_for(anchors))
    processor = scripted_processor(env, script)
    running = await _claim(env, filename="prov.docx", content=content)

    finished = await processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert len(env.replay.progress.notes) >= 2, "the batches publish before the final save"
    assert set(env.replay.progress.notes) == {()}
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    assert opened.notes == ()


@pytest.mark.asyncio
async def test_pdf_import_runs_the_word_job_and_opens_version_one():
    env = pdf_environment()
    running = await pdf_claim(env)
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_docx is None
    assert env.replay.provider.requests == []
    assert env.replay.progress.calls == ["publish_final"]
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    chunks = PdfPlumberExamChunker().chunk(content=PDF_CORPUS.read_bytes()).chunks
    chunk_text = {c.anchor: c.text.strip() for c in chunks if not is_answer_line_chunk(c)}
    items = opened.document.items
    assert [item.source_anchor for item in items] == list(chunk_text)
    stripped = 0
    for item in items:
        full = chunk_text[item.source_anchor or ""]
        first = item.plain_text_lines()[0].split("\n")[0]
        expected = full.split("\n")[0]
        if first != expected:
            # The review-item builder strips a printed points label from the first line,
            # as in the Word import; the full chunk text stays on the import record.
            assert POINT_LABEL.sub("", expected).rstrip() == first, item.source_anchor
            assert item.import_record is not None
            assert full in item.import_record.original_wording.question_text
            stripped += 1
    assert 0 < stripped < len(items)


@pytest.mark.asyncio
async def test_a_pdf_import_records_a_pdf_origin():
    env = pdf_environment()
    running = await _claim(
        env,
        filename="sidfot-lasforstaelse.pdf",
        content=PDF_CORPUS.read_bytes(),
    )
    opened = await _open_finished(env, running)
    assert opened.document.origin.kind == "pdf_import"
    assert opened.document.origin.source_filename == "sidfot-lasforstaelse.pdf"
    assert opened.document.origin.extractor_version == "docx_ai_build_v2"


@pytest.mark.asyncio
async def test_a_pdf_with_a_skipped_page_publishes_the_note_with_the_exam():
    env = pdf_environment()
    content = merged(
        pdf_bytes("<p>1. Vad heter huvudpersonen?</p>"),
        pdf_bytes("<p></p>"),
        pdf_bytes("<p>2. Vilken färg har båten?</p>"),
    )
    running = await _claim(env, filename="prov-med-tom-sida.pdf", content=content)

    opened = await _open_finished(env, running)

    note = "Sida 2 importerades inte eftersom texten inte gick att läsa in."
    assert opened.notes[0] == note
    assert note in opened.notes


@pytest.mark.asyncio
async def test_a_pdf_without_readable_text_finishes_failed_with_the_new_message():
    env = pdf_environment()
    running = await _claim(env, filename="utan-text.pdf", content=pdf_bytes("<p></p>"))

    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.source_docx is None
    status = await GetExamWorkspaceConversionStatusHandler(jobs=env.jobs, index=env.index).handle(
        actor=env.actor, job_id=running.id
    )
    assert status.error_message == NO_READABLE_TEXT


@pytest.mark.asyncio
async def test_a_word_import_keeps_a_word_origin():
    env = pdf_environment()
    content = corpus_docx("chapter_4_poetry_and_lyrics_quiz_med_facit")
    running = await _claim(env, filename="prov.docx", content=content)
    opened = await _open_finished(env, running)
    assert opened.document.origin.kind == "docx_import"
    assert opened.document.origin.source_filename == "prov.docx"
    assert opened.document.origin.extractor_version == "docx_ai_build_v2"


@pytest.mark.asyncio
async def test_a_pdf_without_a_printed_title_takes_its_title_from_the_filename():
    env = pdf_environment()
    running = await _claim(
        env,
        filename="Engelska 1 - facit.pdf",
        content=PDF_CORPUS.read_bytes(),
    )
    opened = await _open_finished(env, running)
    assert opened.document.title == "Engelska 1.pdf"
