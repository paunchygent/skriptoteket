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
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
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
    PdfPlumberExamChunker,
)
from tests.fixtures.docx_corpus import corpus_docx
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    InMemoryEnrichmentJobRepository,
    replayed_docx_job_handler,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import Replay
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _Env,
    _settings,
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
    chunks = PdfPlumberExamChunker().chunk(content=PDF_CORPUS.read_bytes())
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
