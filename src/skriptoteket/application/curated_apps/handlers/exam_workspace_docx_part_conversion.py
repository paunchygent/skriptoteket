"""Convert and admit one DOCX batch part, preserving source and infrastructure failures.

Unavailable source and converter/content failures become review outcomes for this part.
Receipt writes share the publication lock and propagate their original storage faults;
a busy door and cancellation also stop conversion rather than becoming source review.
"""

from __future__ import annotations

import asyncio

import structlog

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    validated,
    with_type_check_mark,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
    convert_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildExchangeProtocol,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_output_observer import (
    DocxReceiptWriteError,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline_batches import (
    BatchPart,
    batch_state,
    failed,
    limited,
    source_reviewed,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.llm_door import AiDailyLimitReached, AiDoorBusy, AiJobOverageCapReached
from skriptoteket.protocols.docx_conversion_progress import DocxConversionProgressProtocol

logger = structlog.get_logger(__name__)


async def admit_part(
    run: DocxConversionRun,
    part: BatchPart,
    *,
    exchange: DocxBuildExchangeProtocol,
    profile: StructuredLLMProviderProfile,
    progress: DocxConversionProgressProtocol,
    progress_lock: asyncio.Lock,
) -> BatchOutcome:
    """One part's outcome: its families' review when their source is unavailable, else
    their admitted and contract-checked items."""
    if part.missing:
        return source_reviewed(run, part)
    if run.ai_limit is not None and run.limit_code is not None:
        return limited(run, part.batch, run.limit_code)

    async def received(question_ids: tuple[str, ...]) -> None:
        async with progress_lock:
            await progress.received(
                worker_id=run.job.worker_id,
                job_id=run.job.job_id,
                question_ids=question_ids,
            )

    try:
        outcome = await convert_batch(
            state=batch_state(run, part.batch),
            batch=part.batch,
            families={
                f.question_id: f for f in run.families if f.question_id in part.batch.question_ids
            },
            exchange=exchange,
            profile=profile,
            caller=run.job.caller,
            on_received=received,
        )
        with_type_check_mark(outcome.state)
        validated(outcome.state)
    except DocxReceiptWriteError as error:
        # Progress-store faults stop the job; they are never source-content failures.
        raise error.error from error
    except AiDoorBusy:
        # A busy door ends the conversion; it never becomes a review item.
        raise
    except (AiDailyLimitReached, AiJobOverageCapReached) as exc:
        code = run.note_limit(exc)
        # One refused batch never fails the conversion (D25): its items fail as for
        # a DocxBuildRoundFailure.
        logger.warning(
            "DOCX conversion batch refused at the door",
            job_id=str(run.job.job_id),
            batch=part.batch.batch_id,
            code=code,
        )
        return failed(run, part.batch, code, exc)
    except Exception as error:
        # One batch's failure never fails the conversion (D25).
        logger.exception(
            "DOCX conversion batch failed",
            job_id=str(run.job.job_id),
            batch=part.batch.batch_id,
        )
        return failed(run, part.batch, "batch_failed", error)
    return outcome
