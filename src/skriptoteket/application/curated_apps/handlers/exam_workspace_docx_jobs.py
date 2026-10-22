"""Complete background DOCX imports and publish their first native revision."""

from __future__ import annotations

import hashlib

import structlog
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionPipelineProtocol,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.curated_apps.exam_workspace.import_file_format import (
    import_origin_kind,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    AiJobOverageCapReached,
    ai_limit_note,
    ai_try_again_note,
    door_caller_for,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.docx_conversion_progress import DocxConversionProgressProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import DocxExamChunkerProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

_Diagnostics = tuple[dict[str, JsonValue], ...]


def _job_failure(code: str, detail: str, observed: _Diagnostics = ()) -> _Diagnostics:
    """Append the terminal job failure to the conversion events already observed."""
    return (*observed, DocxBuildEvent(stage="job", code=code, detail=detail).as_json())


class ProcessExamWorkspaceDocxJobHandler:
    """Build outside a transaction, then fence document publication with the job row."""

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        chunker: DocxExamChunkerProtocol,
        pipeline: DocxConversionPipelineProtocol,
        progress: DocxConversionProgressProtocol,
        store: ExamWorkspaceDocumentStore,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._chunker = chunker
        self._pipeline = pipeline
        self._progress = progress
        self._store = store
        self._users = users
        self._uow = uow
        self._clock = clock
        self._ids = id_generator

    async def handle(
        self, *, job: ExamAnswerKeyEnrichmentJob, fallback_reason: str | None = None
    ) -> ExamAnswerKeyEnrichmentJob:
        if job.source_docx is None or job.workspace_lineage_id is None or job.locked_by is None:
            raise ValueError("Unfinished DOCX jobs require their source, lineage and claim.")
        observed: _Diagnostics = ()
        try:
            actor = await self._users.get_by_id(job.owner_user_id)
            if actor is None:
                return await self._fail(
                    job,
                    "Kontot för provdokumentet finns inte längre.",
                    _job_failure("owner_missing", str(job.owner_user_id)),
                )
            outcome = await self._pipeline.convert(
                job=DocxConversionJob(
                    job_id=job.id,
                    worker_id=job.locked_by,
                    document_id=job.workspace_lineage_id,
                    filename=job.input_filename,
                    source_sha256=hashlib.sha256(job.source_docx).hexdigest(),
                    source_docx=job.source_docx,
                    chunks=self._chunker.chunk(content=job.source_docx),
                    course_key=job.workspace_course_key,
                    caller=door_caller_for(user=actor),
                    origin_kind=import_origin_kind(job.source_docx),
                ),
                fallback_reason=fallback_reason,
            )
            result = outcome.result
            observed = tuple(event.as_json() for event in result.events)
            if outcome.ai_limit is not None:
                # A door limit anywhere in the conversion ends the job as failed:
                # already-published batches and teacher edits stay, but the partial
                # or source-review document is never advertised as a completed conversion.
                code = outcome.limit_code or "ai_daily_limit"
                return await self._fail(
                    job,
                    ai_limit_note(outcome.ai_limit),
                    _job_failure(code, outcome.ai_limit.value, observed),
                    ai_limit=outcome.ai_limit,
                )
            file_id = self._ids.new_uuid()
            async with self._store.transaction(
                user_id=actor.id, lineage_id=job.workspace_lineage_id
            ):
                current = await self._jobs.get_by_id_for_update(job_id=job.id)
                if not self._owns(current, job):
                    return current or job
                assert current is not None
                await self._progress.publish_final(
                    worker_id=job.locked_by,
                    job_id=job.id,
                    lineage_id=job.workspace_lineage_id,
                    actor=actor,
                    file_id=file_id,
                    update=outcome.update,
                    notes=result.notes,
                )
                finished = finish_enrichment_job(
                    job=current,
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=self._clock.now(),
                    diagnostics=observed,
                ).model_copy(update={"source_docx": None})
                updated = await self._jobs.update(job=finished, expected_worker_id=job.locked_by)
            logger.info(
                "DOCX conversion job succeeded",
                job_id=str(job.id),
                items=len(result.document.items),
                review_items=sum(bool(item.review.reasons) for item in result.document.items),
                failure_events=sum(event.stage != "formatting" for event in result.events),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                timings={t.stage: round(t.finished_seconds, 2) for t in result.timings},
            )
            return updated
        except DomainError as error:
            return await self._fail(
                job, error.message, _job_failure("domain_error", error.code.value, observed)
            )
        except AiJobOverageCapReached:
            return await self._fail(
                job,
                ai_limit_note(AiDailyLimit.POOL),
                _job_failure("ai_overage_cap", "AiJobOverageCapReached", observed),
                ai_limit=AiDailyLimit.POOL,
            )
        except AiDailyLimitReached as error:
            return await self._fail(
                job,
                ai_limit_note(error.limit),
                _job_failure("ai_daily_limit", type(error).__name__, observed),
                ai_limit=error.limit,
            )
        except AiDoorBusy as error:
            # A busy door is no limit: the job records no ``ai_limit`` and asks to try again.
            return await self._fail(
                job,
                ai_try_again_note(),
                _job_failure("ai_door_busy", type(error).__name__, observed),
            )
        except Exception as error:
            logger.exception("DOCX conversion job crashed", job_id=str(job.id))
            return await self._fail(
                job,
                "Konverteringen stoppades av ett oväntat fel. Försök igen eller kontakta support.",
                _job_failure("unexpected_error", type(error).__name__, observed),
            )

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
        self,
        job: ExamAnswerKeyEnrichmentJob,
        message: str,
        diagnostics: _Diagnostics,
        ai_limit: AiDailyLimit | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        logger.warning(
            "DOCX conversion job failed",
            job_id=str(job.id),
            last_error=message,
            diagnostics=diagnostics,
        )
        assert job.workspace_lineage_id is not None
        async with self._store.transaction(
            user_id=job.owner_user_id, lineage_id=job.workspace_lineage_id
        ):
            current = await self._jobs.get_by_id_for_update(job_id=job.id)
            if not self._owns(current, job):
                return current or job
            assert current is not None
            if ai_limit is not None:
                current = current.model_copy(update={"ai_limit": ai_limit})
            if job.locked_by is not None:
                await self._progress.abandon(worker_id=job.locked_by, job_id=job.id, reason=message)
            finished = finish_enrichment_job(
                job=current,
                status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                now=self._clock.now(),
                last_error=message,
                diagnostics=diagnostics,
            ).model_copy(update={"source_docx": None})
            return await self._jobs.update(job=finished, expected_worker_id=job.locked_by)
