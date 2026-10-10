"""Complete background DOCX imports and publish their first native revision."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    DocxExamChunkerProtocol,
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ProcessExamWorkspaceDocxJobHandler:
    """Build outside a transaction, then fence document publication with the job row."""

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        chunker: DocxExamChunkerProtocol,
        converter: DocxAIConverter,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._chunker = chunker
        self._converter = converter
        self._codec = codec
        self._store = store
        self._users = users
        self._uow = uow
        self._clock = clock
        self._ids = id_generator

    async def handle(
        self, *, job: ExamAnswerKeyEnrichmentJob, fallback_reason: str | None = None
    ) -> ExamAnswerKeyEnrichmentJob:
        if job.source_docx is None or job.workspace_lineage_id is None:
            raise ValueError("Unfinished DOCX jobs require their source and lineage.")
        try:
            actor = await self._users.get_by_id(job.owner_user_id)
            if actor is None:
                return await self._fail(job, "Kontot för provdokumentet finns inte längre.")
            chunks = self._chunker.chunk(content=job.source_docx)
            result = await self._converter.convert(
                job_id=job.id,
                document_id=job.workspace_lineage_id,
                filename=job.input_filename,
                source_sha256=hashlib.sha256(job.source_docx).hexdigest(),
                chunks=chunks,
                fallback_reason=fallback_reason,
            )
            content = self._codec.build(
                content=ExamWorkspaceContainerContent(
                    document=result.document,
                    assets_by_id={},
                    notes=result.notes,
                )
            )
            async with self._uow:
                current = await self._jobs.get_by_id_for_update(job_id=job.id)
                if not self._owns(current, job):
                    return current or job
                assert current is not None
                await self._store.save_version(
                    actor=actor,
                    file_id=self._ids.new_uuid(),
                    name=f"{PurePosixPath(job.input_filename).stem}.provdokument.zip",
                    content=content,
                    lineage_id=job.workspace_lineage_id,
                    version=1,
                )
                finished = finish_enrichment_job(
                    job=current,
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=self._clock.now(),
                ).model_copy(update={"source_docx": None})
                return await self._jobs.update(job=finished, expected_worker_id=job.locked_by)
        except DomainError as error:
            return await self._fail(job, error.message)

    def _owns(
        self, current: ExamAnswerKeyEnrichmentJob | None, claimed: ExamAnswerKeyEnrichmentJob
    ) -> bool:
        return bool(
            current is not None
            and current.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING
            and current.locked_by == claimed.locked_by
            and current.locked_until is not None
            and current.locked_until > self._clock.now()
        )

    async def _fail(
        self, job: ExamAnswerKeyEnrichmentJob, message: str
    ) -> ExamAnswerKeyEnrichmentJob:
        async with self._uow:
            current = await self._jobs.get_by_id_for_update(job_id=job.id)
            if not self._owns(current, job):
                return current or job
            assert current is not None
            finished = finish_enrichment_job(
                job=current,
                status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                now=self._clock.now(),
                last_error=message,
            ).model_copy(update={"source_docx": None})
            return await self._jobs.update(job=finished, expected_worker_id=job.locked_by)
