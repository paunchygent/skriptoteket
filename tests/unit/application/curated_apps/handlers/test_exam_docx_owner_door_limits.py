"""Door-limit tests for the DOCX import job's owner handling.

Purpose:
    Prove the DOCX workspace job resolves its owner before converting: the
    conversion job carries the owner's caller (an admin owner is exempt and
    never allowed paid overage), and a missing owner fails the job with no
    conversion started.

Relationships:
    Exercises ``ProcessExamWorkspaceDocxJobHandler`` with a capturing
    ``DocxConversionPipeline`` subclass; the answer-key workspace lane's
    limit, cap and busy proofs live in ``test_exam_answer_key_door_limits``.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
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
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    UUIDGenerator,
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
)
from tests.unit.llm_door_fakes import user_with_role

pytestmark = pytest.mark.unit


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
