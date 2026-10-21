"""A text PDF enters the existing Word import lane; anything else is refused."""

from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDigiExamDocumentHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    InMemoryEnrichmentJobRepository,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _settings,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_import_course import (
    importer,
)

PDF_CORPUS = Path(
    "tests/fixtures/exam_conversion/pdf_corpus/bf26_english_1_unit_test_kap_1_2_med_facit.pdf"
)
DOCX_CORPUS = Path(
    "tests/fixtures/exam_conversion/docx_corpus/bf26_english_1_unit_test_kap_1_2_med_facit.docx"
)


def _digiexam_importer():
    jobs = InMemoryEnrichmentJobRepository()
    uow = FakeUow()
    handler = ImportExamWorkspaceDigiExamDocumentHandler(
        jobs=jobs,
        uow=uow,
        clock=FixedClock(_NOW),
        settings=_settings(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )
    return handler, jobs, uow


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", ["prov.pdf", "PROV.PDF"])
async def test_text_pdf_queues_a_word_lane_job(filename):
    handler, jobs, uow = importer()
    content = PDF_CORPUS.read_bytes()
    status = await handler.handle(
        actor=_actor(), filename=filename, content=content, course_key=None
    )
    assert status.state == "queued"
    job = jobs.jobs[status.job_id]
    assert job.source_kind is ExamAnswerKeySourceKind.DOCX_IMPORT
    assert job.source_docx == content
    assert job.source_dxe is None
    assert job.input_filename == filename
    assert uow.entered and uow.exited


@pytest.mark.asyncio
async def test_pdf_named_docx_bytes_are_rejected_without_queuing():
    handler, jobs, uow = importer()
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_actor(),
            filename="prov.pdf",
            content=DOCX_CORPUS.read_bytes(),
            course_key=None,
        )
    assert error.value.code == ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Filen kunde inte läsas som en PDF-fil (.pdf)."
    assert jobs.jobs == {}
    assert not uow.entered


@pytest.mark.asyncio
async def test_unknown_extension_is_rejected_without_queuing():
    handler, jobs, uow = importer()
    with pytest.raises(DomainError) as error:
        await handler.handle(actor=_actor(), filename="prov.txt", content=b"text", course_key=None)
    assert error.value.code == ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Välj en .docx-fil eller .pdf-fil."
    assert jobs.jobs == {}
    assert not uow.entered


@pytest.mark.asyncio
async def test_empty_pdf_is_rejected_without_queuing():
    handler, jobs, uow = importer()
    with pytest.raises(DomainError) as error:
        await handler.handle(actor=_actor(), filename="prov.pdf", content=b"", course_key=None)
    assert error.value.code == ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Filen saknar innehåll."
    assert jobs.jobs == {}
    assert not uow.entered


@pytest.mark.asyncio
async def test_digiexam_lane_still_refuses_pdf():
    handler, jobs, uow = _digiexam_importer()
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_actor(),
            filename="prov.pdf",
            content=PDF_CORPUS.read_bytes(),
            course_key=None,
        )
    assert error.value.code == ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Välj en .dxe-fil."
    assert jobs.jobs == {}
    assert not uow.entered
