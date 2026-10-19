"""A picked course survives queued DOCX import; invalid keys never create jobs."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
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


def importer():
    jobs = InMemoryEnrichmentJobRepository()
    uow = FakeUow()
    handler = ImportExamWorkspaceDocumentHandler(
        jobs=jobs,
        uow=uow,
        clock=FixedClock(_NOW),
        settings=_settings(),
        id_generator=SequenceIdGenerator([uuid4(), uuid4()]),
    )
    return handler, jobs, uow


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "supplied,stored",
    [
        ("SVESVE02", "SVESVE02"),
        ("  SVESVE02\t", "SVESVE02"),
        ("GRGRSVE01/7-9", "GRGRSVE01/7-9"),
        (None, None),
        ("", None),
        (" \t\n ", None),
    ],
)
async def test_queued_import_carries_the_optional_course_key(supplied, stored):
    handler, jobs, uow = importer()
    # The import boundary queues opaque DOCX bytes; parsing belongs to the worker.
    content = b"queued DOCX source"
    status = await handler.handle(
        actor=_actor(), filename="Svenska 2.docx", content=content, course_key=supplied
    )
    assert status.state == "queued"
    job = jobs.jobs[status.job_id]
    assert job.workspace_course_key == stored
    assert job.source_docx == content
    assert job.workspace_lineage_id == status.lineage_id
    assert uow.entered and uow.exited


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["X" * 65, "NOT-A-SKOLVERKET-COURSE"])
async def test_invalid_course_key_is_a_named_validation_error_without_queuing(key):
    handler, jobs, uow = importer()
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=_actor(), filename="prov.docx", content=b"source", course_key=key
        )
    assert error.value.code == ErrorCode.VALIDATION_ERROR
    assert error.value.details.get("field") == "course_key"
    assert jobs.jobs == {}
    assert not uow.entered
