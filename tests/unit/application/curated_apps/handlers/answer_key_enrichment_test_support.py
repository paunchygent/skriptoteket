"""In-memory fakes and builders for the machine answer-key enrichment tests.

Purpose:
    Give the enrichment lifecycle tests protocol fakes for the
    enrichment repository, scripted structured providers,
    provider-route builders, and the DOCX import processor wiring the enrichment dispatcher
    requires.

Relationships:
    - Shared by the dispatcher, workspace enrichment, DOCX job, and repository
      tests that reuse its fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    ExamWorkspaceConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol
from skriptoteket.protocols.exam_workspace import (
    DocxExamChunkerProtocol,
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RecordingProgress,
    Replay,
    build_replay,
)
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

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class UUIDGenerator:
    def new_uuid(self) -> UUID:
        return uuid4()


class InMemoryEnrichmentJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ExamAnswerKeyEnrichmentJob] = {}

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        self.jobs[job.id] = job
        return job

    async def update(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        expected_worker_id: str | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        current = self.jobs.get(job.id)
        if (
            expected_worker_id is not None
            and current is not None
            and current.locked_by != expected_worker_id
        ):
            raise AssertionError("worker lease is no longer owned")
        # Like the PostgreSQL repository, update never writes the conversion progress.
        self.jobs[job.id] = job.model_copy(
            update={"conversion_progress": current.conversion_progress if current else None}
        )
        return self.jobs[job.id]

    async def set_conversion_progress(
        self, *, job_id: UUID, progress: dict[str, JsonValue]
    ) -> None:
        self.jobs[job_id] = self.jobs[job_id].model_copy(update={"conversion_progress": progress})

    async def get_conversion_view(self, *, job_id: UUID) -> ExamWorkspaceConversionJobView | None:
        job = self.jobs.get(job_id)
        return (
            ExamWorkspaceConversionJobView.model_validate(job, from_attributes=True)
            if job
            else None
        )

    async def lock_conversion_view_by_lineage(
        self, *, owner_user_id: UUID, workspace_lineage_id: UUID
    ) -> ExamWorkspaceConversionJobView | None:
        for job in self.jobs.values():
            if (
                job.source_kind == ExamAnswerKeySourceKind.DOCX_IMPORT
                and job.owner_user_id == owner_user_id
                and job.workspace_lineage_id == workspace_lineage_id
            ):
                return ExamWorkspaceConversionJobView.model_validate(job, from_attributes=True)
        return None

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        return self.jobs.get(job_id)

    async def get_by_id_for_update(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        return self.jobs.get(job_id)

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self.jobs.values():
            if job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED and (
                source_kind is None or job.source_kind is source_kind
            ):
                claimed = job.model_copy(
                    update={
                        "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
                        "attempts": job.attempts + 1,
                        "locked_by": worker_id,
                        "locked_until": now + lease_ttl,
                        "updated_at": now,
                    }
                )
                self.jobs[job.id] = claimed
                return claimed
        return None

    async def claim_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        source_kind: ExamAnswerKeySourceKind | None = None,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self.jobs.values():
            if (
                job.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING
                and job.locked_until is not None
                and job.locked_until < now
                and (source_kind is None or job.source_kind is source_kind)
            ):
                claimed = job.model_copy(
                    update={
                        "locked_by": worker_id,
                        "locked_until": now + lease_ttl,
                        "updated_at": now,
                    }
                )
                self.jobs[job.id] = claimed
                return claimed
        return None

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.locked_by != worker_id:
            return False
        self.jobs[job_id] = job.model_copy(
            update={"locked_until": now + lease_ttl, "updated_at": now}
        )
        return True


class StubProvider:
    def __init__(self, *, content: dict[str, JsonValue], usage: StructuredLLMUsage) -> None:
        self._content = content
        self._usage = usage
        self.call_count = 0

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> StructuredLLMResponse:
        self.call_count += 1
        return StructuredLLMResponse(
            content=self._content,
            finish_reason="completed",
            usage=self._usage,
        )


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
        reasoning_effort=StructuredLLMReasoningEffort.LOW,
    )


DEFAULT_REPLAYED_EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"


def docx_job_handler(
    *,
    enrichment_jobs: InMemoryEnrichmentJobRepository,
    provider: AnswerKeyStructuredProviderProtocol,
    vault_files: InMemoryVaultFileRepository,
    vault_storage: InMemoryVaultStorage,
    codec: ExamWorkspaceContainerCodecProtocol,
) -> ProcessExamWorkspaceDocxJobHandler:
    """The DOCX import processor the dispatcher requires; ``provider`` is unused (replayed)."""
    handler, _ = replayed_docx_job_handler(
        enrichment_jobs=enrichment_jobs,
        vault_files=vault_files,
        vault_storage=vault_storage,
        codec=codec,
    )
    return handler


def replayed_docx_job_handler(
    *,
    enrichment_jobs: InMemoryEnrichmentJobRepository,
    vault_files: InMemoryVaultFileRepository,
    vault_storage: InMemoryVaultStorage,
    codec: ExamWorkspaceContainerCodecProtocol,
    exam: str = DEFAULT_REPLAYED_EXAM,
    store: ExamWorkspaceDocumentStore | None = None,
    users: UserRepositoryProtocol | None = None,
    enabled: bool = True,
    chunker: DocxExamChunkerProtocol | None = None,
) -> tuple[ProcessExamWorkspaceDocxJobHandler, Replay]:
    """The DOCX processor over ``exam``'s replayed pipeline and the production progress port."""
    uow = FakeUow()
    clock = FixedClock(_NOW)
    id_generator = UUIDGenerator()
    users = users or UserRepositoryStub()
    store = store or ExamWorkspaceDocumentStore(
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=_NOW)
        ),
        vault_storage=vault_storage,
        index=InMemoryExamIndexRepository(vault_files),
        codec=codec,
        uow=uow,
        clock=clock,
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=5_000_000,
            VAULT_MAX_TOTAL_BYTES=50_000_000,
        ),
    )
    progress = RecordingProgress(
        inner=ExamWorkspaceConversionProgress(
            jobs=enrichment_jobs,
            users=users,
            vault_files=vault_files,
            store=store,
            codec=codec,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )
    )
    replay = build_replay(exam, progress=progress, enabled=enabled)
    handler = ProcessExamWorkspaceDocxJobHandler(
        jobs=enrichment_jobs,
        chunker=chunker if chunker is not None else PythonDocxExamChunker(),
        pipeline=replay.pipeline,
        progress=progress,
        store=store,
        users=users,
        uow=uow,
        clock=clock,
        id_generator=id_generator,
    )
    return handler, replay
