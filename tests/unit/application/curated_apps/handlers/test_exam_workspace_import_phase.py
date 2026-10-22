"""A Word or PDF import is queued already reading, so the teacher sees the phase and
its clock from the upload response on (TASK-SKRIPT-39-04-23 walk D1)."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDigiExamDocumentHandler,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionPhase
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
from tests.unit.application.curated_apps.handlers.test_exam_workspace_pdf_import import (
    PDF_CORPUS,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,content",
    [
        pytest.param("prov.docx", b"queued DOCX source", id="word"),
        pytest.param("prov.pdf", PDF_CORPUS.read_bytes(), id="pdf"),
    ],
)
async def test_a_word_or_pdf_import_is_queued_already_reading(filename: str, content: bytes):
    handler, jobs, _ = importer()

    status = await handler.handle(
        actor=_actor(), filename=filename, content=content, course_key=None
    )

    assert status.state == "queued"
    assert status.phase is ConversionPhase.READING
    assert status.phase_started_at == _NOW
    stored = jobs.jobs[status.job_id]
    assert stored.conversion_phase is ConversionPhase.READING
    assert stored.conversion_phase_started_at == _NOW


@pytest.mark.asyncio
async def test_a_digiexam_import_is_queued_without_a_phase():
    jobs = InMemoryEnrichmentJobRepository()
    handler = ImportExamWorkspaceDigiExamDocumentHandler(
        jobs=jobs,
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        settings=_settings(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )

    status = await handler.handle(
        actor=_actor(), filename="prov.dxe", content=b"dxe-bytes", course_key=None
    )

    assert status.phase is None and status.phase_started_at is None
    assert jobs.jobs[status.job_id].conversion_phase is None
