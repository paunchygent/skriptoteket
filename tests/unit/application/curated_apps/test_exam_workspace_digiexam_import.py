"""DigiExam uploads queue exactly one native-workspace import, never a DOCX job."""

from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDigiExamDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
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

_FIXTURES = Path("tests/fixtures/exam_conversion")
_REAL_EXAMS = (
    _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe",
    _FIXTURES / "sanitized-embedded-image.dxe",
    _FIXTURES / "real_inputs/1776888013-ak7-lag-och-ratt.dxe",
)


def _importer(handler_type=ImportExamWorkspaceDigiExamDocumentHandler, *, max_bytes=None):
    jobs = InMemoryEnrichmentJobRepository()
    uow = FakeUow()
    settings = _settings()
    if max_bytes is not None:
        settings = settings.model_copy(update={"VAULT_MAX_FILE_BYTES": max_bytes})
    handler = handler_type(
        jobs=jobs,
        uow=uow,
        clock=FixedClock(_NOW),
        settings=settings,
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )
    return handler, jobs, uow


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture", _REAL_EXAMS, ids=lambda path: path.stem)
async def test_real_export_queues_once_with_source_course_and_private_status(fixture):
    handler, jobs, uow = _importer()
    actor = _actor()
    content = fixture.read_bytes()
    queued = await handler.handle(
        actor=actor, filename=fixture.name, content=content, course_key="  SVESVE02\t"
    )
    assert queued.state == "queued"
    assert len(jobs.jobs) == 1
    job = jobs.jobs[queued.job_id]
    assert job.source_kind.value == "digiexam_import"
    assert job.source_dxe == content
    assert job.source_docx is None
    assert job.owner_user_id == actor.id
    assert job.workspace_lineage_id == queued.lineage_id
    assert job.workspace_document_revision == 1
    assert job.workspace_course_key == "SVESVE02"
    assert uow.entered and uow.exited

    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.get.return_value = None
    status_handler = GetExamWorkspaceConversionStatusHandler(jobs=jobs, index=index)
    observed = await status_handler.handle(actor=actor, job_id=queued.job_id)
    assert observed == queued
    assert "source_dxe" not in observed.model_dump()
    with pytest.raises(DomainError) as error:
        await status_handler.handle(actor=_actor(), job_id=queued.job_id)
    assert error.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,content,course_key,max_bytes,field",
    [
        ("prov.docx", b"not a dxe", None, None, None),
        ("prov.pdf", b"not a dxe", None, None, None),
        ("prov.dxe.docx", b"not a dxe", None, None, None),
        ("prov.dxe", b"", None, None, None),
        ("prov.dxe", b"1234", None, 3, None),
        ("prov.dxe", b"source", "NOT-A-COURSE", None, "course_key"),
        ("prov.dxe", b"source", "X" * 65, None, "course_key"),
    ],
)
async def test_invalid_upload_is_rejected_before_any_job_or_transaction(
    filename, content, course_key, max_bytes, field
):
    handler, jobs, uow = _importer(max_bytes=max_bytes)
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_actor(), filename=filename, content=content, course_key=course_key
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    if field:
        assert error.value.details.get("field") == field
    assert jobs.jobs == {}
    assert not uow.entered


@pytest.mark.asyncio
async def test_docx_route_stays_docx_only():
    handler, jobs, uow = _importer(ImportExamWorkspaceDocumentHandler)
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_actor(),
            filename=_REAL_EXAMS[0].name,
            content=_REAL_EXAMS[0].read_bytes(),
            course_key=None,
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert jobs.jobs == {}
    assert not uow.entered


@pytest.mark.asyncio
async def test_dxe_suffix_is_case_insensitive_and_no_course_is_required():
    handler, jobs, _ = _importer()
    queued = await handler.handle(
        actor=_actor(),
        filename="Prov.DXE",
        content=b"worker validates the contents",
        course_key=None,
    )
    assert jobs.jobs[queued.job_id].workspace_course_key is None
    assert jobs.jobs[queued.job_id].input_filename == "Prov.DXE"
