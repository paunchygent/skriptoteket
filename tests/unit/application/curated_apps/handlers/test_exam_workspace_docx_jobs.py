"""Background import publication, source deletion, readback and upload validation."""

import json
from datetime import timedelta
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeItemReviewState,
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
    replayed_docx_job_handler,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import CORPUS, Replay
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _Env,
    _settings,
)

_QUIZ_EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_QUIZ = CORPUS / f"{_QUIZ_EXAM}.docx"


class JobEnvironment(_Env):
    jobs: InMemoryEnrichmentJobRepository
    actor: User
    replay: Replay
    importer: ImportExamWorkspaceDocumentHandler
    processor: ProcessExamWorkspaceDocxJobHandler


def environment(*, enabled: bool = True, budget: int = 1_000_000) -> JobEnvironment:
    """The DOCX job over the production pipeline replaying the quiz's live recordings."""
    env = JobEnvironment()
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
        proposed_overlays=env.proposed_overlays,
        leases=InMemoryLeaseRepository(daily_token_limit=budget),
        vault_files=env.vault_files,
        vault_storage=env.vault_storage,
        codec=env.codec,
        exam=_QUIZ_EXAM,
        store=env.store,
        users=AsyncMock(get_by_id=AsyncMock(return_value=env.actor)),
        enabled=enabled,
    )
    return env


async def claim(env: JobEnvironment, content: bytes | None = None) -> ExamAnswerKeyEnrichmentJob:
    status = await env.importer.handle(
        actor=env.actor,
        filename=_QUIZ.name,
        content=content if content is not None else _QUIZ.read_bytes(),
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


@pytest.mark.asyncio
async def test_recorded_live_quiz_publishes_version_one_and_reports_every_batch_to_progress():
    env = environment()
    running = await claim(env)
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_docx is None
    batches = [i for i in env.replay.provider.request_ids if i.startswith("docx_w")]
    assert len(batches) > 1
    assert env.replay.progress.calls == [
        "outline",
        *["batch_ready"] * len(batches),
        "publish_final",
    ]
    # Reply w1-01 lists q5's own lead-in body:0018 only as an instruction; it stays with q5 under
    # the item's check mark (D41).
    assert [(d["code"], d["anchors"]) for d in finished.diagnostics] == [
        ("instructions_own_chunk", ["body:0018"]),
        ("own_chunks_left_out", ["body:0018"]),
    ]
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    document = opened.document
    assert len(env.replay.progress.finals) == 1
    assert len(document.items) == 28
    assert [item.kind.value for item in document.items] == ["single_choice"] * 21 + ["gap_fill"] * 7
    assert all(item.points is not None for item in document.items)
    assert sum(item.points for item in document.items if item.points is not None) == 28
    assert all(item.review.parse_origin.value == "llm_parsed" for item in document.items)
    assert all(item.answer_key.origin.value == "source_provided" for item in document.items)
    assert [(b.item_id, b.reason) for b in native_export_blockers(document)] == [
        ("item_005", "review_required")
    ]
    # The teacher handles the check mark; then the quiz exports.
    reviewed = tuple(
        item.model_copy(
            update={
                "review": item.review.model_copy(
                    update={"state": NativeItemReviewState.REVIEW_COMPLETE}
                )
            }
        )
        if item.item_id == "item_005"
        else item
        for item in document.items
    )
    package_bytes, report_bytes = build_native_examnet_qti_package(
        document.model_copy(update={"items": reviewed}),
        package_name="poetry",
        qti_writer=ExamNetQtiPackageWriter(),
    )
    assert package_bytes.startswith(b"PK")
    assert json.loads(report_bytes)["package_status"] == "passed"


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,budget", [(False, 1_000_000), (True, 1)])
async def test_unavailable_budget_or_provider_opens_review_source_and_deletes_docx(enabled, budget):
    env = environment(enabled=enabled, budget=budget)
    running = await claim(env)
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.source_docx is None
    assert env.replay.provider.requests == []
    assert env.replay.progress.calls == ["publish_final"]
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
    assert env.replay.progress.calls == ["abandon"]
    assert env.replay.provider.requests == []
    assert finished.diagnostics == (
        {
            "stage": "job",
            "code": "domain_error",
            "batch": None,
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
