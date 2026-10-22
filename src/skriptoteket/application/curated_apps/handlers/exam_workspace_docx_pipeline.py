"""Type-batched parallel DOCX conversion (TASK-SKRIPT-39-05-04 steps 1-4, D25, D29).

One grouping call maps the questions, one labeling call types them, and type batches
convert concurrently in two waves: questions the first labeling pass accepts convert at
once; each question the second pass decides converts as soon as its label arrives.
Each admitted batch reaches the progress port as a provisional document; the final
document is assembled in source order and checked against the grouping.

Each question reaches the labeler as its faithful source: markdown, with an image of each
block markdown cannot carry (D14). A question holding a block of which no faithful image
could be made is not labeled: the event names the block, and the question converts as free
text with no label confidence, so it carries the type-check mark. A question neither labeling
pass gave any label is not converted: it becomes one review item holding its own source text
at its place, for the teacher to label. An unsupported label converts as free text; a
question the second pass leaves unresolved arrives with the first pass's top label (D23).
The strict schema is the
only gate on a batch response. A family the converter reports as a type conflict is resent
with the reported kind, the only resend. A family that still conflicts in its resend is
kept as converted and carries the type-check mark: its review confidence stays below the
acceptance threshold. Chunks no batch converts become review items.

A fault in one question only ever affects that question. Every item a batch admits is
checked against the native contract inside the batch, and an item that fails becomes a
review item holding its own source text. A batch that raises, or whose merge into the
document fails on content, leaves each of its questions as one review item holding the
question's source text at its place, and every other batch's result stays. The merge runs on
a copy of the document-wide state, so a failed merge changes nothing. Only infrastructure
faults stop the conversion: the progress port's database and job-lock faults, and
cancellation.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import replace

import structlog

from skriptoteket.application.curated_apps.exam_content_tagging import (
    ExamContentTagSuggester,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    merge_batch,
    validated,
    with_type_check_mark,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
    convert_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_content_suggest import (
    suggest_content_tags,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_labeling import (
    labeling_request,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline_batches import (
    BatchPart,
    batch_state,
    failed,
    limited,
    reviewed,
    source_parts,
    source_reviewed,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_publication import (
    final_publication,
    provisional_publication,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionOutcome,
    DocxConversionRun,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    pack_batches,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    claim_inner_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    assign_question_headings,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.llm_door import AiDailyLimitReached, AiDoorBusy, AiJobOverageCapReached
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionPhase,
    ConversionUpdate,
    DocxConversionProgressProtocol,
    OutlineQuestion,
)
from skriptoteket.protocols.exam_grouping import ExamGrouperProtocol, ExamGroupingError
from skriptoteket.protocols.exam_workspace import LabelerSourceProtocol
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabelerProtocol,
    ItemTypeLabelResult,
    LabelingRequest,
    LabelPass,
)

_KIND_OF_LABEL: dict[ItemTypeLabel, NativeExamItemKind] = {
    ItemTypeLabel.SINGLE_CHOICE: NativeExamItemKind.SINGLE_CHOICE,
    ItemTypeLabel.MULTIPLE_RESPONSE: NativeExamItemKind.MULTIPLE_RESPONSE,
    ItemTypeLabel.GAP_FILL: NativeExamItemKind.GAP_FILL,
    ItemTypeLabel.FREE_TEXT: NativeExamItemKind.FREE_TEXT,
    ItemTypeLabel.MATCHING: NativeExamItemKind.MATCHING,
    ItemTypeLabel.UNSUPPORTED: NativeExamItemKind.FREE_TEXT,
}
_DISABLED_REASON = "AI-tolkning är avstängd. Kontrollera källtexten manuellt."
_LABELING_REASON = "Frågetyperna kunde inte avgöras. Kontrollera källtexten manuellt."
_GROUPING_LIMIT_REASON = "Provets struktur kunde inte läsas ut. Kontrollera källtexten manuellt."
UNLABELED_REASON = "Frågetypen kunde inte avgöras. Välj frågetyp och kontrollera källtexten."

logger = structlog.get_logger(__name__)


class DocxConversionPipeline:
    """Group, label and convert type batches concurrently into one native exam."""

    def __init__(
        self,
        *,
        grouper: ExamGrouperProtocol,
        labeler: ItemTypeLabelerProtocol,
        labeler_source: LabelerSourceProtocol,
        exchange: DocxBuildRoundExchange,
        profile: StructuredLLMProviderProfile,
        progress: DocxConversionProgressProtocol,
        uow: SerializedUnitOfWork,
        families_per_batch: int,
        enabled: bool,
        content_classifier: ExamContentTagSuggester | None = None,
    ) -> None:
        self._grouper = grouper
        self._labeler = labeler
        self._labeler_source = labeler_source
        self._exchange = exchange
        self._profile = profile
        self._progress = progress
        self._uow = uow
        self._families_per_batch = families_per_batch
        self._enabled = enabled
        self._content_classifier = content_classifier

    async def convert(
        self, *, job: DocxConversionJob, fallback_reason: str | None = None
    ) -> DocxConversionOutcome:
        run = DocxConversionRun(job, time.monotonic())
        if fallback_reason or not self._enabled:
            reason = fallback_reason or _DISABLED_REASON
            run.state.record(
                "fallback", "lease_expired" if fallback_reason else "ai_disabled", detail=reason
            )
            run.state.fail_all_pending(reason)
            return final_publication(run, None)
        await self._report_phase(run, ConversionPhase.FINDING)
        started = time.monotonic()
        try:
            grouping = await self._grouper.group(
                job_id=job.job_id, chunks=job.chunks, caller=job.caller
            )
        except (AiDailyLimitReached, AiJobOverageCapReached) as exc:
            code = run.note_limit(exc)
            run.state.record("grouping", code, detail=type(exc).__name__)
            run.state.fail_all_pending(_GROUPING_LIMIT_REASON)
            return final_publication(run, None)
        except ExamGroupingError as error:
            run.state.record("grouping", error.code, detail=error.detail)
            run.state.fail_all_pending(str(error))
            return final_publication(run, None)
        for usage in grouping.usage:
            run.state.record_usage(usage)
        run.timed("grouping", started)
        manifest = claim_inner_chunks(
            assign_points_lines(
                assign_question_headings(grouping.manifest, job.chunks), job.chunks
            ),
            job.chunks,
        )
        run.manifest = manifest
        run.state.header_anchors = frozenset(h.anchor for h in manifest.header)
        run.families = question_families(manifest, job.chunks)
        run.title_anchors = frozenset(manifest.title_anchors)
        run.context_anchors = frozenset(context.anchor for context in manifest.contexts)
        run.contexts = manifest.contexts
        for question in manifest.questions:
            run.own_anchors[question.question_id] = (*question.anchors, *question.subpart_anchors)
            run.key_anchors[question.question_id] = question.key_anchors
        await self._outline(run, manifest)
        await self._report_phase(run, ConversionPhase.SORTING)
        request, unlabeled = labeling_request(run, manifest, self._labeler_source)
        optional = (
            asyncio.create_task(
                suggest_content_tags(run, manifest, request, self._content_classifier)
            )
            if self._content_classifier is not None
            else None
        )
        try:
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(self._label_and_convert(run, request, unlabeled, tasks))
        except* (DomainError, AiDoorBusy) as group:
            # A busy door stops the conversion like a domain error: the job handler
            # fails the job with the try-again note, and in-flight batches are cancelled.
            raise group.exceptions[0] from group
        finally:
            # This conversion owns the optional request's entire lifetime. Keep
            # ready tags; cancel and join unfinished work on success or failure.
            # Provider timeouts must never hold up an otherwise complete exam.
            if optional is not None:
                optional.cancel()
                await asyncio.gather(optional, return_exceptions=True)
        return final_publication(run, manifest)

    async def _report_phase(self, run: DocxConversionRun, phase: ConversionPhase) -> None:
        async with self._uow.lock:
            await self._progress.phase(
                worker_id=run.job.worker_id, job_id=run.job.job_id, phase=phase
            )

    async def _outline(self, run: DocxConversionRun, manifest: ExamManifest) -> None:
        questions = tuple(
            OutlineQuestion(
                question_id=family.question_id,
                position=family.position,
                anchors=family.question_anchors,
                source_text="\n".join(
                    run.state.chunk_by_anchor[a].text for a in family.question_anchors
                ),
            )
            for family in run.families
        )
        title = " ".join(run.state.chunk_by_anchor[a].text for a in manifest.title_anchors)
        async with self._uow.lock:
            await self._progress.outline(
                worker_id=run.job.worker_id,
                job_id=run.job.job_id,
                outline=ConversionOutline(title=title or None, questions=questions),
            )

    async def _label_and_convert(
        self,
        run: DocxConversionRun,
        request: LabelingRequest,
        unlabeled: list[str],
        tasks: asyncio.TaskGroup,
    ) -> None:
        started = time.monotonic()
        for question_id in unlabeled:
            run.kinds[question_id] = NativeExamItemKind.FREE_TEXT
            run.label_kinds[question_id] = NativeExamItemKind.FREE_TEXT
        if unlabeled:
            self._dispatch(run, unlabeled, "wi-", tasks)
        if run.ai_limit is not None and run.limit_code is not None:
            run.state.record("labeling", run.limit_code, detail="limit_already_recorded")
            run.state.fail_all_pending(_LABELING_REASON)
            return

        def _note_run_limit(exc: AiDailyLimitReached | AiJobOverageCapReached) -> None:
            run.note_limit(exc)

        def settle(results: tuple[ItemTypeLabelResult, ...]) -> None:
            if not results:
                return
            if results[0].decided_by is LabelPass.FIRST:
                run.timed("labeling_first_pass", started)
                prefix = "w1-"
            else:
                # Each second-pass label converts at once; a per-dispatch number keeps
                # every second-wave batch id unique.
                run.second_wave_dispatches += 1
                prefix = f"w2-{run.second_wave_dispatches:02d}-"
            labeled: list[str] = []
            unlabeled: list[str] = []
            for result in results:
                if result.label is ItemTypeLabel.UNRESOLVED:
                    run.state.record(
                        "labeling",
                        "question_unlabeled",
                        anchors=run.own_anchors[result.item_id],
                        detail=result.failure_code or "",
                    )
                    run.label_kinds[result.item_id] = NativeExamItemKind.FREE_TEXT
                    unlabeled.append(result.item_id)
                    continue
                run.kinds[result.item_id] = _KIND_OF_LABEL[result.label]
                run.label_kinds[result.item_id] = _KIND_OF_LABEL[result.label]
                labeled.append(result.item_id)
            self._dispatch(run, labeled, prefix, tasks)
            if unlabeled:
                tasks.create_task(self._unlabeled(run, unlabeled, f"{prefix}u", tasks))

        try:
            await self._labeler.label(request=request, on_results=settle, on_limit=_note_run_limit)
        except (AiDailyLimitReached, AiJobOverageCapReached) as exc:
            code = run.note_limit(exc)
            run.state.record("labeling", code, detail=type(exc).__name__)
            run.state.fail_all_pending(_LABELING_REASON)
            return
        except ItemTypeLabelerError as error:
            run.state.record("labeling", error.code, detail=str(error.status_code or ""))
            run.state.fail_all_pending(_LABELING_REASON)
            return
        run.timed("labeling", started)

    def _dispatch(
        self, run: DocxConversionRun, question_ids: list[str], prefix: str, tasks: asyncio.TaskGroup
    ) -> None:
        chosen = set(question_ids)
        families = tuple(f for f in run.families if f.question_id in chosen)
        batches = pack_batches(
            families, run.kinds, families_per_batch=self._families_per_batch, prefix=prefix
        )
        if batches and not run.converting_reported:
            # The first dispatch of any batch, labelled or not, starts the converting phase.
            # This task is created first, so it takes the unit-of-work lock before any batch
            # delivers.
            run.converting_reported = True
            tasks.create_task(self._report_phase(run, ConversionPhase.CONVERTING))
        for batch in batches:
            tasks.create_task(self._convert(run, batch, tasks))

    async def _convert(
        self, run: DocxConversionRun, batch: ConversionBatch, tasks: asyncio.TaskGroup
    ) -> None:
        started = time.monotonic()
        parts = source_parts(run, batch)
        outcomes = [await self._admitted(run, part) for part in parts]
        run.timed(f"batch {batch.batch_id}", started)
        for part, outcome in zip(parts, outcomes, strict=True):
            await self._deliver(run, part.batch, outcome, tasks)

    async def _unlabeled(
        self,
        run: DocxConversionRun,
        question_ids: list[str],
        batch_id: str,
        tasks: asyncio.TaskGroup,
    ) -> None:
        """Questions no labeling pass labeled, each as one review item of its source text."""
        chosen = set(question_ids)
        families = tuple(f for f in run.families if f.question_id in chosen)
        batch = ConversionBatch(
            batch_id=batch_id,
            kinds=frozenset(),
            question_ids=tuple(f.question_id for f in families),
            claims=frozenset().union(*(f.claims for f in families)),
            reads=frozenset(),
        )
        await self._deliver(run, batch, reviewed(run, batch, UNLABELED_REASON), tasks)

    async def _deliver(
        self,
        run: DocxConversionRun,
        batch: ConversionBatch,
        outcome: BatchOutcome,
        tasks: asyncio.TaskGroup,
    ) -> None:
        async with self._uow.lock:
            try:
                update = self._merged(run, batch, outcome)
            except Exception as error:
                # The merge ran on a copy, so the document-wide state is unchanged (D25).
                logger.exception(
                    "DOCX conversion batch merge failed",
                    job_id=str(run.job.job_id),
                    batch=batch.batch_id,
                )
                outcome = failed(run, batch, "batch_merge_failed", error)
                update = self._merged(run, batch, outcome)
            await self._progress.batch_ready(
                worker_id=run.job.worker_id, job_id=run.job.job_id, update=update
            )
        if outcome.conflicts:
            self._dispatch(run, list(outcome.conflicts), f"{batch.batch_id}c", tasks)

    async def _admitted(self, run: DocxConversionRun, part: BatchPart) -> BatchOutcome:
        """One part's outcome: its families' review when their source is unavailable, else
        their admitted and contract-checked items."""
        if part.missing:
            return source_reviewed(run, part)
        if run.ai_limit is not None and run.limit_code is not None:
            return limited(run, part.batch, run.limit_code)
        try:
            outcome = await convert_batch(
                state=batch_state(run, part.batch),
                batch=part.batch,
                families={
                    f.question_id: f
                    for f in run.families
                    if f.question_id in part.batch.question_ids
                },
                exchange=self._exchange,
                profile=self._profile,
                caller=run.job.caller,
            )
            with_type_check_mark(outcome.state)
            validated(outcome.state)
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

    def _merged(
        self, run: DocxConversionRun, batch: ConversionBatch, outcome: BatchOutcome
    ) -> ConversionUpdate:
        """Merge the batch into a copy of the document and build its provisional update; the
        run takes the copy only when every step succeeded."""
        trial = run.state.snapshot()
        families = tuple(
            replace(f, claims=outcome.released[f.question_id])
            if f.question_id in outcome.released
            else f
            for f in run.families
        )
        merge_batch(trial, outcome.state, run.title_anchors)
        filled = (*run.filled, *(q for q in batch.question_ids if q not in outcome.conflicts))
        pending = tuple(f.question_id for f in families if f.question_id not in filled)
        update = provisional_publication(run, trial, families, filled, pending)
        run.state = trial
        run.families = families
        run.filled = list(filled)
        for qid, kind in outcome.conflicts.items():
            run.kinds[qid] = kind
            run.resent.add(qid)
        return update
