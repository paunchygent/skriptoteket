"""Background import publication, source deletion, readback and upload validation."""

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    native_export_blockers,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    InMemoryEnrichmentJobRepository,
    InMemoryLeaseRepository,
    StubProvider,
    _route,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _Env,
    _settings,
)

_QUIZ = Path(
    "tests/fixtures/exam_conversion/docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx"
)
_RESPONSE = Path("tests/fixtures/exam_conversion/chapter_4_poetry_docx_build_response.json")
_COURSE_EXAM = Path(
    "tests/fixtures/exam_conversion/docx_corpus/svenska_2_kursavslutande_prov_med_facit.docx"
)
_COURSE_RESPONSE = Path(
    "tests/fixtures/exam_conversion/svenska_2_kursavslutande_prov_docx_build_response_v2.json"
)


class RecordedRoundsProvider(StubProvider):
    """Replay the recorded live round on every call."""

    def __init__(self, response: Path) -> None:
        super().__init__(content=json.loads(response.read_text()), usage=StructuredLLMUsage())


class JobEnvironment(_Env):
    jobs: InMemoryEnrichmentJobRepository
    actor: User
    provider: StubProvider
    importer: ImportExamWorkspaceDocumentHandler
    processor: ProcessExamWorkspaceDocxJobHandler


def environment(
    *, enabled: bool = True, budget: int = 1_000_000, response: Path = _RESPONSE
) -> JobEnvironment:
    env = JobEnvironment()
    env.jobs = InMemoryEnrichmentJobRepository()
    env.actor = _actor()
    env.provider = RecordedRoundsProvider(response)
    env.importer = ImportExamWorkspaceDocumentHandler(
        jobs=env.jobs,
        uow=env.store._uow,
        clock=FixedClock(_NOW),
        settings=_settings(),
        id_generator=env.ids,
    )
    converter = DocxAIConverter(
        provider=env.provider,
        profile=_route().primary,
        leases=InMemoryLeaseRepository(daily_token_limit=budget),
        uow=env.store._uow,
        clock=FixedClock(_NOW),
        enabled=enabled,
    )
    env.processor = ProcessExamWorkspaceDocxJobHandler(
        jobs=env.jobs,
        chunker=PythonDocxExamChunker(),
        converter=converter,
        codec=env.codec,
        store=env.store,
        users=AsyncMock(get_by_id=AsyncMock(return_value=env.actor)),
        uow=env.store._uow,
        clock=FixedClock(_NOW),
        id_generator=env.ids,
    )
    return env


async def claim(env: JobEnvironment, content: bytes | None = None) -> ExamAnswerKeyEnrichmentJob:
    status = await env.importer.handle(
        actor=env.actor,
        filename=_QUIZ.name,
        content=content if content is not None else _QUIZ.read_bytes(),
    )
    assert status.state == "queued"
    assert env.provider.call_count == 0
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


@pytest.mark.asyncio
async def test_recorded_live_quiz_publishes_version_one_and_persists_round_diagnostics():
    env = environment()
    running = await claim(env)
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_docx is None
    # The recorded live round claimed every chunk, so no further round and no failure event.
    assert env.provider.call_count == 1
    assert finished.diagnostics == ()
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    assert opened.summary.version == 1
    document = opened.document
    assert len(document.items) == 28
    assert [item.kind.value for item in document.items] == ["single_choice"] * 21 + ["gap_fill"] * 7
    assert all(item.points is not None for item in document.items)
    assert sum(item.points for item in document.items if item.points is not None) == 28
    assert [item.answer_key.correct_choice_ids for item in document.items[:21]] == [
        (f"choice_{i:03d}",)
        for i in [1, 3, 2, 4, 2, 4, 3, 1, 1, 8, 2, 5, 6, 4, 3, 2, 1, 6, 3, 4, 7]
    ]
    assert [item.gaps[0].accepted_values for item in document.items[21:]] == [
        (v,)
        for v in [
            "cherish",
            "traverse",
            "humiliate",
            "out of the blue",
            "line",
            "diction",
            "alliteration",
        ]
    ]
    assert all(item.review.parse_origin.value == "llm_parsed" for item in document.items)
    assert all(item.answer_key.origin.value == "source_provided" for item in document.items)
    assert native_export_blockers(document) == ()
    package_bytes, report_bytes = build_native_examnet_qti_package(
        document, package_name="poetry", qti_writer=ExamNetQtiPackageWriter()
    )
    assert package_bytes.startswith(b"PK")
    assert json.loads(report_bytes)["package_status"] == "passed"


@pytest.mark.asyncio
async def test_recorded_model_reviews_persist_their_reasons_in_job_diagnostics():
    env = environment(response=_COURSE_RESPONSE)
    running = await claim(env, _COURSE_EXAM.read_bytes())
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert env.provider.call_count == 1
    prefix = "AI-tolkningen markerade frågan för granskning: "
    assert [e["detail"] for e in finished.diagnostics if e["code"] == "model_review"] == [
        *[f"{prefix}Uppgiftens svarssätt framgår inte av källtexten."] * 4,
        f"{prefix}Uppgiften saknar instruktion om hur påståendena ska besvaras.",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,budget", [(False, 1_000_000), (True, 1)])
async def test_unavailable_budget_or_provider_opens_review_source_and_deletes_docx(enabled, budget):
    env = environment(enabled=enabled, budget=budget)
    running = await claim(env)
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_docx is None
    assert env.provider.call_count == 0
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    chunks = PythonDocxExamChunker().chunk(content=_QUIZ.read_bytes())
    assert [item.plain_text_lines()[0] for item in opened.document.items] == [
        c.text.strip() for c in chunks
    ]
    assert all(item.review.state.value == "review_required" for item in opened.document.items)
    assert opened.notes
    assert native_export_blockers(opened.document)
    codes = {event["code"] for event in finished.diagnostics}
    assert codes == {"ai_disabled" if not enabled else "lease_refused", "review_item"}
    reason = opened.document.items[0].review.reasons[0]
    assert reason == (
        "AI-tolkning är avstängd. Kontrollera källtexten manuellt."
        if not enabled
        else "Dagens AI-budget är förbrukad. Kontrollera källtexten manuellt."
    )


@pytest.mark.asyncio
async def test_invalid_docx_finishes_failed_and_deletes_source():
    env = environment()
    running = await claim(env, b"invalid docx")
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.source_docx is None
    status = await GetExamWorkspaceConversionStatusHandler(jobs=env.jobs).handle(
        actor=env.actor, job_id=running.id
    )
    assert status.error_message and "Word" in status.error_message
    assert finished.diagnostics == (
        {
            "stage": "job",
            "code": "domain_error",
            "round": None,
            "item": None,
            "anchors": [],
            "detail": "VALIDATION_ERROR",
        },
    )


@pytest.mark.asyncio
async def test_status_owner_authorization_and_upload_validation():
    env = environment()
    running = await claim(env)
    status = GetExamWorkspaceConversionStatusHandler(jobs=env.jobs)
    with pytest.raises(DomainError):
        await status.handle(actor=_actor(), job_id=running.id)
    with pytest.raises(DomainError):
        await status.handle(actor=env.actor, job_id=uuid4())
    for filename, content in [("exam.pdf", b"x"), ("exam.docx", b"")]:
        with pytest.raises(DomainError):
            await env.importer.handle(actor=env.actor, filename=filename, content=content)
