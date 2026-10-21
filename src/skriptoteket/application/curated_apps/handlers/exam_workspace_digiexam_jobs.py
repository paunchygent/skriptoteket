"""Publish one bare DigiExam import under the durable conversion job's claim."""

from __future__ import annotations

import hashlib

import structlog

from skriptoteket.application.curated_apps.digiexam_source_parsing import parse_source_exam
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    ConversionUnit,
    ConversionUnitState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.domain.curated_apps.exam_workspace.digiexam_import import (
    build_native_exam_from_digiexam,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_conversion import EmbeddedImageDecodabilityProtocol
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class ProcessExamWorkspaceDigiExamJobHandler:
    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        image_decodability: EmbeddedImageDecodabilityProtocol,
    ) -> None:
        self._jobs = jobs
        self._store = store
        self._users = users
        self._clock = clock
        self._ids = id_generator
        self._codec = codec
        self._image_decodability = image_decodability

    def _owns(
        self, current: ExamAnswerKeyEnrichmentJob | None, job: ExamAnswerKeyEnrichmentJob
    ) -> bool:
        return bool(
            current is not None
            and current.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING
            and current.locked_by == job.locked_by
            and current.locked_until is not None
            and current.locked_until > self._clock.now()
        )

    async def handle(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        fallback_reason: str | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        if job.source_dxe is None or job.workspace_lineage_id is None or job.locked_by is None:
            raise ValueError("DigiExam imports require source, lineage and claim")
        if fallback_reason is not None:
            return await self._fail(job, fallback_reason)
        try:
            actor = await self._users.get_by_id(job.owner_user_id)
            if actor is None:
                return await self._fail(job, "Kontot för provdokumentet finns inte längre.")
            course = next(
                (
                    course
                    for course in load_exam_course_catalog().courses
                    if course.key == job.workspace_course_key
                ),
                None,
            )
            exam = parse_source_exam(
                upload=ConversionHubUpload(
                    filename=job.input_filename,
                    content_type="application/octet-stream",
                    file_bytes=job.source_dxe,
                ),
                image_decodability=self._image_decodability,
            )
            container = build_native_exam_from_digiexam(
                exam=exam,
                document_id=job.workspace_lineage_id,
                source_sha256=hashlib.sha256(job.source_dxe).hexdigest(),
                course=None
                if course is None
                else ExamCourseChoice(key=course.key, name=course.name),
            )
            content = self._codec.build(content=container)
            progress = ConversionProgress(
                revision=1,
                units=tuple(
                    ConversionUnit(
                        unit_id=item.item_id,
                        question=True,
                        state=ConversionUnitState.READY,
                        item_ids=(item.item_id,),
                        digest=hashlib.sha256(item.model_dump_json().encode()).hexdigest(),
                    )
                    for item in container.document.items
                ),
            )
            async with self._store.transaction(
                user_id=actor.id, lineage_id=job.workspace_lineage_id
            ):
                current = await self._jobs.get_by_id_for_update(job_id=job.id)
                if not self._owns(current, job):
                    return current or job
                assert current is not None
                await self._store.save(
                    actor=actor,
                    file_id=self._ids.new_uuid(),
                    name=f"{container.document.title}.provdokument.zip",
                    content=content,
                    lineage_id=job.workspace_lineage_id,
                    version=1,
                )
                await self._jobs.set_conversion_progress(
                    job_id=job.id, progress=progress.model_dump(mode="json")
                )
                finished = finish_enrichment_job(
                    job=current,
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=self._clock.now(),
                ).model_copy(update={"source_dxe": None})
                return await self._jobs.update(job=finished, expected_worker_id=job.locked_by)
        except DomainError as error:
            return await self._fail(job, error.message)
        except Exception:
            logger.exception("DigiExam workspace import failed", job_id=str(job.id))
            return await self._fail(
                job, "DigiExam-exporten kunde inte importeras. Försök igen eller kontakta support."
            )

    async def _fail(
        self, job: ExamAnswerKeyEnrichmentJob, message: str
    ) -> ExamAnswerKeyEnrichmentJob:
        assert job.workspace_lineage_id is not None
        async with self._store.transaction(
            user_id=job.owner_user_id, lineage_id=job.workspace_lineage_id
        ):
            current = await self._jobs.get_by_id_for_update(job_id=job.id)
            if not self._owns(current, job):
                return current or job
            assert current is not None
            finished = finish_enrichment_job(
                job=current,
                status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                now=self._clock.now(),
                last_error=message,
            ).model_copy(update={"source_dxe": None})
            return await self._jobs.update(job=finished, expected_worker_id=job.locked_by)
