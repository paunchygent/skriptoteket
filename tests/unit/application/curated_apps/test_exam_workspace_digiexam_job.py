"""Real DigiExam source survives background publication and stale workers cannot publish."""

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
    ImportExamWorkspaceDigiExamDocumentHandler,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.identity import UserRepositoryProtocol
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _Env,
    _settings,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")
_REAL_EXAMS = (
    (_FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe", 7),
    (_FIXTURES / "sanitized-embedded-image.dxe", 1),
    (_FIXTURES / "real_inputs/1776888013-ak7-lag-och-ratt.dxe", 8),
)


def _environment():
    env = _Env()
    actor = _actor()
    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = actor
    importer = ImportExamWorkspaceDigiExamDocumentHandler(
        jobs=env.enrichment_jobs,
        uow=env.store._uow,
        clock=FixedClock(_NOW),
        settings=_settings(),
        id_generator=env.ids,
    )
    processor = ProcessExamWorkspaceDigiExamJobHandler(
        jobs=env.enrichment_jobs,
        store=env.store,
        users=users,
        uow=env.store._uow,
        clock=FixedClock(_NOW),
        id_generator=env.ids,
        codec=env.codec,
    )
    return env, actor, users, importer, processor


async def _claim(env, actor, importer, *, filename, content):
    status = await importer.handle(
        actor=actor, filename=filename, content=content, course_key="SVESVE02"
    )
    job = await env.enrichment_jobs.claim_next(
        worker_id="dxe-worker", now=_NOW, lease_ttl=timedelta(minutes=10)
    )
    assert job is not None and job.id == status.job_id
    return job


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture,item_count", _REAL_EXAMS, ids=lambda value: str(value))
async def test_fixture_import_saves_first_native_revision_and_reopens_without_source(
    fixture, item_count
):
    env, actor, _, importer, processor = _environment()
    content = fixture.read_bytes()
    job = await _claim(env, actor, importer, filename=fixture.name, content=content)
    assert env.vault_files.files == {}, "upload must not publish before background parsing"
    finished = await processor.handle(job=job)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_dxe is None
    assert len(env.vault_files.files) == 1
    opened = await env.get_handler.handle(actor=actor, lineage_id=job.workspace_lineage_id)
    document = opened.document
    assert document.revision == opened.summary.version == 1
    assert document.document_id == job.workspace_lineage_id
    assert document.origin.kind == "digiexam_import"
    assert document.origin.source_filename == fixture.name
    assert document.origin.source_sha256 == hashlib.sha256(content).hexdigest()
    assert len(document.items) == item_count
    assert document.title
    assert document.header.course.key == "SVESVE02"
    assert all(item.review.parse_origin.value != "llm_parsed" for item in document.items)
    status = await GetExamWorkspaceConversionStatusHandler(
        jobs=env.enrichment_jobs, index=env.index
    ).handle(actor=actor, job_id=job.id)
    assert status.state == "succeeded"
    assert status.document_revision == 1


@pytest.mark.asyncio
async def test_embedded_image_bytes_survive_container_readback():
    env, actor, _, importer, processor = _environment()
    fixture = _FIXTURES / "sanitized-embedded-image.dxe"
    job = await _claim(env, actor, importer, filename=fixture.name, content=fixture.read_bytes())
    finished = await processor.handle(job=job)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    stored = next(iter(env.vault_files.files.values()))
    payload = await env.vault_storage.read_file(user_id=actor.id, file_id=stored.id)
    # Decode the actual saved bytes, not the mapper's in-memory asset dictionary.
    decoded = env.codec.parse(content=payload)
    assert len(decoded.document.assets) == len(decoded.assets_by_id) == 1
    asset = decoded.document.assets[0]
    image = decoded.assets_by_id[asset.asset_id]
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    assert stored.document_version == 1


@pytest.mark.asyncio
async def test_unsupported_question_is_omitted_and_named_in_saved_notes():
    env, actor, _, importer, processor = _environment()
    fixture = _FIXTURES / "1772718003-test-samma-prov-i-digiexam.dxe"
    source = json.loads(fixture.read_bytes())
    source["exams"][0]["questions"][2]["type"] = 99
    job = await _claim(
        env,
        actor,
        importer,
        filename=fixture.name,
        content=json.dumps(source, ensure_ascii=False).encode(),
    )
    finished = await processor.handle(job=job)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    opened = await env.get_handler.handle(actor=actor, lineage_id=job.workspace_lineage_id)
    assert len(opened.document.items) == 6
    notes = " ".join(opened.notes)
    assert "3" in notes
    assert "Så här ser en annan flervalsfråga" in notes


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["expired", "reclaimed", "completed"])
async def test_worker_without_current_claim_cannot_publish_a_document(state):
    env, actor, _, importer, processor = _environment()
    fixture = _REAL_EXAMS[0][0]
    job = await _claim(env, actor, importer, filename=fixture.name, content=fixture.read_bytes())
    updates = {
        "expired": {"locked_until": _NOW - timedelta(seconds=1)},
        "reclaimed": {"locked_by": "new-worker"},
        "completed": {"status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED},
    }
    current = job.model_copy(update=updates[state])
    env.enrichment_jobs.jobs[job.id] = current
    observed = await processor.handle(job=job)
    assert observed == current
    assert env.vault_files.files == {}
    assert env.vault_storage.stored == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [b"not a DigiExam export", b"\xff\xfe", b'{"exams": []}'])
async def test_unparseable_source_finishes_failed_without_publishing(content):
    env, actor, _, importer, processor = _environment()
    job = await _claim(env, actor, importer, filename="broken.dxe", content=content)
    failed = await processor.handle(job=job)
    assert failed.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert failed.source_dxe is None
    assert failed.last_error
    assert env.vault_files.files == {}
    with pytest.raises(DomainError):
        await env.get_handler.handle(actor=actor, lineage_id=job.workspace_lineage_id)
