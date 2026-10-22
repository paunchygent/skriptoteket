"""Door-limit tests for the answer-key workspace lane.

Purpose:
    Prove the workspace suggestion job runs through the provider door with
    the owner's caller: an admin owner is sent exempt, a door limit on a
    later item keeps the suggestions already collected and ends the job with
    the limit note and ``ai_limit`` set, a started job finishes as paid
    overage while a later job meets the limit, and the per-job overage cap
    stops a job through the same failure path, and a busy door on a later item
    ends the job with the try-again note and no ``ai_limit``. Also proves the
    DOCX job carries the owner's caller.

Relationships:
    Exercises the enrichment workspace lane and the DOCX job handler with a
    real ``OpenAIAnswerKeyStructuredProvider`` over
    ``tests.unit.llm_door_fakes.RecordingDoor``.
"""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceEnrichmentState
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionOutcome,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
    WorkspaceAnswerKeySuggestionsPayload,
    suggestions_response_for_job,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import answer_key_item_views
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    ai_limit_note,
    ai_try_again_note,
)
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.llm_door import DoorReply
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    StubProvider,
    UUIDGenerator,
    _profile,
    docx_job_handler,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import RecordingProgress
from tests.unit.application.curated_apps.handlers.exam_index_test_support import (
    InMemoryExamIndexRepository,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.application.curated_apps.handlers.workspace_enrichment_job_support import (
    NOW,
    three_unkeyed_choice_document,
    unkeyed_choice_document,
)
from tests.unit.llm_door_fakes import DoorSent, RecordingDoor, json_reply, user_with_role

pytestmark = pytest.mark.unit


def _responses_body(choice_index: int) -> dict:
    return {
        "status": "completed",
        "output_text": json.dumps({"correct_alternative_ids": [choice_index]}),
    }


class DoorHarness:
    """The enrichment processor with a real door-backed provider over a fake door."""

    def __init__(
        self,
        *,
        door: RecordingDoor,
        document: NativeExamDocument,
        owner_role: Role = Role.USER,
    ) -> None:
        self.owner_user_id = uuid4()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.door = door
        self.document = document
        self.users = UserRepositoryStub()
        self.users.user = user_with_role(owner_role, user_id=self.owner_user_id)
        self.handler = ProcessExamAnswerKeyEnrichmentJobHandler(
            enrichment_jobs=self.enrichment_jobs,
            provider=OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0),
            users=self.users,
            answer_key_profile=_profile(),
            uow=FakeUow(),
            clock=FixedClock(NOW),
            digiexam_handler=AsyncMock(spec=ProcessExamWorkspaceDigiExamJobHandler),
            content_tags_handler=AsyncMock(spec=ProcessExamContentSuggestionsHandler),
            docx_handler=docx_job_handler(
                enrichment_jobs=self.enrichment_jobs,
                provider=StubProvider(content={}, usage=StructuredLLMUsage(total_tokens=1)),
                vault_files=InMemoryVaultFileRepository(),
                vault_storage=InMemoryVaultStorage(),
                codec=ExamWorkspaceContainerCodec(),
            ),
        )

    async def seed_claimed_job(self) -> ExamAnswerKeyEnrichmentJob:
        from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
            enqueue_workspace_enrichment_job,
        )

        views = answer_key_item_views(self.document)
        await self.enrichment_jobs.create(
            job=enqueue_workspace_enrichment_job(
                job_id=uuid4(),
                owner_user_id=self.owner_user_id,
                input_filename=self.document.title,
                workspace_lineage_id=self.document.document_id,
                workspace_document_revision=self.document.revision,
                workspace_request_json=WorkspaceAnswerKeyRequestPayload(views=views).model_dump(
                    mode="json"
                ),
                now=NOW,
            )
        )
        claimed = await self.enrichment_jobs.claim_next(
            worker_id="worker-1",
            now=NOW,
            lease_ttl=timedelta(seconds=900),
        )
        assert claimed is not None
        return claimed


async def test_admin_owner_is_sent_exempt_with_the_owner_id() -> None:
    document = unkeyed_choice_document(document_id=uuid4())
    door = RecordingDoor(lambda sent: json_reply(_responses_body(2)))
    harness = DoorHarness(door=door, document=document, owner_role=Role.ADMIN)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert len(door.sent) == 1
    caller = door.sent[0].caller
    assert caller.user_id == harness.owner_user_id
    assert caller.exempt is True
    assert door.sent[0].allow_paid_overage is False


async def test_non_admin_owner_is_sent_not_exempt() -> None:
    document = unkeyed_choice_document(document_id=uuid4())
    door = RecordingDoor(lambda sent: json_reply(_responses_body(2)))
    harness = DoorHarness(door=door, document=document, owner_role=Role.USER)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert door.sent[0].caller.user_id == harness.owner_user_id
    assert door.sent[0].caller.exempt is False
    assert door.sent[0].allow_paid_overage is False


async def test_limit_on_the_second_item_keeps_the_first_suggestion() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())

    def respond(sent: DoorSent) -> DoorReply:
        if len(door.sent) == 2:
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        return json_reply(_responses_body(2))

    door = RecordingDoor(respond)
    harness = DoorHarness(door=door, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_daily_limit"
    assert finished.ai_limit is AiDailyLimit.POOL
    assert len(door.sent) == 2
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001"]
    response = suggestions_response_for_job(finished, lineage_id=document.document_id)
    assert response.state is ExamWorkspaceEnrichmentState.FAILED
    assert response.message == ai_limit_note(AiDailyLimit.POOL)


async def test_limit_on_the_second_item_with_user_share_uses_the_user_note() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())

    def respond(sent: DoorSent) -> DoorReply:
        if len(door.sent) == 2:
            raise AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)
        return json_reply(_responses_body(2))

    door = RecordingDoor(respond)
    harness = DoorHarness(door=door, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_daily_limit"
    assert finished.ai_limit is AiDailyLimit.USER_SHARE
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001"]
    response = suggestions_response_for_job(finished, lineage_id=document.document_id)
    assert response.state is ExamWorkspaceEnrichmentState.FAILED
    assert response.message == ai_limit_note(AiDailyLimit.USER_SHARE)


async def test_busy_door_on_the_second_item_ends_the_job_with_the_try_again_note() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())

    def respond(sent: DoorSent) -> DoorReply:
        if len(door.sent) == 2:
            raise AiDoorBusy(retry_after_seconds=4)
        return json_reply(_responses_body(2))

    door = RecordingDoor(respond)
    harness = DoorHarness(door=door, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_door_busy"
    assert finished.ai_limit is None
    assert len(door.sent) == 2, "no third call after a busy door"
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001"]
    response = suggestions_response_for_job(finished, lineage_id=document.document_id)
    assert response.state is ExamWorkspaceEnrichmentState.FAILED
    assert response.ai_limit is None
    assert response.message == ai_try_again_note()


async def test_started_job_finishes_as_overage_while_a_later_job_meets_the_limit() -> None:
    calls = 0

    def respond(sent: DoorSent) -> DoorReply:
        nonlocal calls
        calls += 1
        if not sent.allow_paid_overage and calls > 1:
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        return json_reply(_responses_body(2))

    first = DoorHarness(
        door=RecordingDoor(respond),
        document=three_unkeyed_choice_document(document_id=uuid4()),
    )
    job1 = await first.seed_claimed_job()
    finished1 = await first.handler.handle(job=job1)

    assert finished1.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert [sent.allow_paid_overage for sent in first.door.sent] == [False, True, True]

    second = DoorHarness(
        door=RecordingDoor(respond),
        document=unkeyed_choice_document(document_id=uuid4()),
    )
    job2 = await second.seed_claimed_job()
    finished2 = await second.handler.handle(job=job2)

    assert finished2.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished2.last_error == "ai_daily_limit"
    assert finished2.ai_limit is AiDailyLimit.POOL
    assert len(second.door.sent) == 1
    response = suggestions_response_for_job(finished2, lineage_id=second.document.document_id)
    assert response.message == ai_limit_note(AiDailyLimit.POOL)


async def test_overage_under_the_cap_completes() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())
    calls = 0

    def respond(sent: DoorSent) -> DoorReply:
        nonlocal calls
        calls += 1
        if calls == 1:
            return json_reply(_responses_body(2))
        return json_reply(_responses_body(2), overage_usd_micros=400_000)

    door = RecordingDoor(respond)
    harness = DoorHarness(door=door, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert len(door.sent) == 3


async def test_a_last_call_whose_overage_passes_the_cap_fails_the_job() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())
    calls = 0

    def respond(sent: DoorSent) -> DoorReply:
        nonlocal calls
        calls += 1
        if calls < 3:
            return json_reply(_responses_body(2))
        return json_reply(_responses_body(2), overage_usd_micros=1_100_000)

    door = RecordingDoor(respond)
    harness = DoorHarness(door=door, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_overage_cap"
    assert finished.ai_limit is AiDailyLimit.POOL
    assert len(door.sent) == 3
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001", "item_002"]
    response = suggestions_response_for_job(finished, lineage_id=document.document_id)
    assert response.message == ai_limit_note(AiDailyLimit.POOL)


class _CapturePipeline(DocxConversionPipeline):
    """Record the conversion job, then stop; the handler fail-closes around it.

    A subclass of the production pipeline so the handler receives the type it
    requires without an unchecked cast; only ``convert`` is replaced.
    """

    def __init__(self) -> None:
        self.job: DocxConversionJob | None = None

    async def convert(
        self, *, job: DocxConversionJob, fallback_reason: str | None = None
    ) -> DocxConversionOutcome:
        self.job = job
        raise RuntimeError("stop after capture")


async def _docx_handler_with_capture(
    *,
    jobs: InMemoryEnrichmentJobRepository,
    users: UserRepositoryProtocol,
    pipeline: _CapturePipeline,
) -> ProcessExamWorkspaceDocxJobHandler:
    from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
        ExamWorkspaceDocumentStore,
    )

    uow = FakeUow()
    clock = FixedClock(NOW)
    vault_files = InMemoryVaultFileRepository()
    store = ExamWorkspaceDocumentStore(
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=NOW)
        ),
        vault_storage=InMemoryVaultStorage(),
        index=InMemoryExamIndexRepository(vault_files),
        codec=ExamWorkspaceContainerCodec(),
        uow=uow,
        clock=clock,
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=5_000_000,
            VAULT_MAX_TOTAL_BYTES=50_000_000,
        ),
    )
    progress = RecordingProgress()
    return ProcessExamWorkspaceDocxJobHandler(
        jobs=jobs,
        chunker=PythonDocxExamChunker(),
        pipeline=pipeline,
        progress=progress,
        store=store,
        users=users,
        uow=uow,
        clock=clock,
        id_generator=UUIDGenerator(),
    )


async def _seed_claimed_docx_job(
    *,
    jobs: InMemoryEnrichmentJobRepository,
    owner_user_id: UUID,
) -> ExamAnswerKeyEnrichmentJob:
    from tests.fixtures.docx_corpus import corpus_docx
    from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
        DEFAULT_REPLAYED_EXAM,
    )

    job = ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        owner_user_id=owner_user_id,
        status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        input_filename="prov.docx",
        source_docx=corpus_docx(DEFAULT_REPLAYED_EXAM),
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        available_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    await jobs.create(job=job)
    claimed = await jobs.claim_next(worker_id="worker-1", now=NOW, lease_ttl=timedelta(seconds=900))
    assert claimed is not None
    return claimed


async def test_docx_job_carries_the_owner_caller() -> None:
    owner_user_id = uuid4()
    users = UserRepositoryStub()
    users.user = user_with_role(Role.ADMIN, user_id=owner_user_id)
    jobs = InMemoryEnrichmentJobRepository()
    pipeline = _CapturePipeline()
    handler = await _docx_handler_with_capture(jobs=jobs, users=users, pipeline=pipeline)
    job = await _seed_claimed_docx_job(jobs=jobs, owner_user_id=owner_user_id)

    await handler.handle(job=job)

    assert pipeline.job is not None
    assert pipeline.job.caller.user_id == owner_user_id
    assert pipeline.job.caller.exempt is True
    assert pipeline.job.caller.allow_paid_overage is False


async def test_missing_docx_owner_fails_with_owner_missing() -> None:
    owner_user_id = uuid4()
    jobs = InMemoryEnrichmentJobRepository()
    pipeline = _CapturePipeline()
    handler = await _docx_handler_with_capture(
        jobs=jobs, users=UserRepositoryStub(), pipeline=pipeline
    )
    job = await _seed_claimed_docx_job(jobs=jobs, owner_user_id=owner_user_id)

    finished = await handler.handle(job=job)

    assert pipeline.job is None
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED


async def test_missing_workspace_owner_fails_with_owner_missing() -> None:
    document = unkeyed_choice_document(document_id=uuid4())
    door = RecordingDoor(lambda sent: json_reply(_responses_body(2)))
    harness = DoorHarness(door=door, document=document)
    harness.users.user = None
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "owner_missing"
    assert len(door.sent) == 0
