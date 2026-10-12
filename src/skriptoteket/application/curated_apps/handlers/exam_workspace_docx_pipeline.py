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
from collections.abc import Mapping
from dataclasses import dataclass, replace
from uuid import UUID

import structlog

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    assembly_check,
    conversion_update,
    governed_anchors,
    merge_batch,
    provisional_result,
    validated,
    with_confidence,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
    convert_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    SourceImage,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult,
    DocxStageTiming,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
    pack_batches,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    SharedContext,
    question_source_anchors,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionUpdate,
    DocxConversionProgressProtocol,
    OutlineQuestion,
)
from skriptoteket.protocols.exam_grouping import ExamGrouperProtocol, ExamGroupingError
from skriptoteket.protocols.exam_workspace import LabelerSource, LabelerSourceProtocol
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabelerProtocol,
    ItemTypeLabelResult,
    LabelingItem,
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
_BATCH_FAILED_REASON = "Frågan kunde inte tolkas. Kontrollera källtexten manuellt."
UNLABELED_REASON = "Frågetypen kunde inte avgöras. Välj frågetyp och kontrollera källtexten."

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DocxConversionOutcome:
    """The final build result and its mapping of grouped questions to items."""

    result: DocxBuildResult
    update: ConversionUpdate


@dataclass(frozen=True)
class DocxConversionJob:
    """Identity and source of one conversion."""

    job_id: UUID
    worker_id: str
    document_id: UUID
    filename: str
    source_sha256: str
    source_docx: bytes
    chunks: tuple[DocxChunk, ...]


class _Run:
    """Mutable bookkeeping of one conversion; every mutation happens under the UoW lock."""

    def __init__(self, job: DocxConversionJob, started: float) -> None:
        self.job = job
        self.started = started
        self.state = DocxBuildState(
            job.job_id, job.document_id, job.filename, job.source_sha256, job.chunks
        )
        self.families: tuple[QuestionFamily, ...] = ()
        self.title_anchors: frozenset[str] = frozenset()
        self.context_anchors: frozenset[str] = frozenset()
        self.contexts: tuple[SharedContext, ...] = ()
        self.own_anchors: dict[str, tuple[str, ...]] = {}
        self.key_anchors: dict[str, tuple[str, ...]] = {}
        self.kinds: dict[str, NativeExamItemKind] = {}
        self.first_pass: dict[str, Mapping[ItemTypeLabel, float]] = {}
        self.resent: set[str] = set()
        self.second_wave_dispatches = 0
        self.filled: list[str] = []
        self.timings: list[DocxStageTiming] = []

    def family(self, question_id: str) -> QuestionFamily:
        return next(f for f in self.families if f.question_id == question_id)

    def timed(self, stage: str, started: float) -> None:
        self.timings.append(
            DocxStageTiming(stage, started - self.started, time.monotonic() - self.started)
        )

    def confidence(self) -> dict[str, float]:
        """The first-pass probability of the label each question converts with."""
        return {
            qid: self.first_pass.get(qid, {}).get(ItemTypeLabel(kind.value), 0.0)
            for qid, kind in self.kinds.items()
        }

    @property
    def pending(self) -> tuple[str, ...]:
        return tuple(f.question_id for f in self.families if f.question_id not in self.filled)


def _labeling_item(
    question_id: str, source: LabelerSource, anchors: frozenset[str]
) -> LabelingItem:
    """The question's block markdown in source order, each block image at its place."""
    text = ""
    images: list[SourceImage] = []
    for chunk in source.chunks:
        if chunk.anchor not in anchors:
            continue
        if chunk.anchor in source.images:
            images.append(SourceImage(source.images[chunk.anchor], len(text)))
            continue
        text = f"{text}\n{chunk.marked_text}" if text else chunk.marked_text
    return LabelingItem(item_id=question_id, source_text=text, images=tuple(images))


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

    async def convert(
        self, *, job: DocxConversionJob, fallback_reason: str | None = None
    ) -> DocxConversionOutcome:
        run = _Run(job, time.monotonic())
        if fallback_reason or not self._enabled:
            reason = fallback_reason or _DISABLED_REASON
            run.state.record(
                "fallback", "lease_expired" if fallback_reason else "ai_disabled", detail=reason
            )
            run.state.fail_all_pending(reason)
            return self._final(run, None)
        started = time.monotonic()
        try:
            grouping = await self._grouper.group(job_id=job.job_id, chunks=job.chunks)
        except ExamGroupingError as error:
            run.state.record("grouping", error.code, detail=error.detail)
            run.state.fail_all_pending(str(error))
            return self._final(run, None)
        for usage in grouping.usage:
            run.state.record_usage(usage)
        run.timed("grouping", started)
        manifest = grouping.manifest
        run.families = question_families(manifest, job.chunks)
        run.title_anchors = frozenset(manifest.title_anchors)
        run.context_anchors = frozenset(context.anchor for context in manifest.contexts)
        run.contexts = manifest.contexts
        for question in manifest.questions:
            run.own_anchors[question.question_id] = (*question.anchors, *question.subpart_anchors)
            run.key_anchors[question.question_id] = question.key_anchors
        await self._outline(run, manifest)
        try:
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(self._label_and_convert(run, manifest, tasks))
        except* DomainError as group:
            raise group.exceptions[0] from group
        return self._final(run, manifest)

    async def _outline(self, run: _Run, manifest: ExamManifest) -> None:
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

    def _labeling_request(
        self, run: _Run, manifest: ExamManifest
    ) -> tuple[LabelingRequest, list[str]]:
        """Each question's faithful source (D14), and the questions holding a block of which
        no faithful image could be made; those are recorded and never labeled."""
        source = self._labeler_source.source(content=run.job.source_docx)
        items: list[LabelingItem] = []
        unlabeled: list[str] = []
        for family in run.families:
            anchors = question_source_anchors(manifest, source.chunks, family.question_id)
            missing = sorted(anchor for anchor in anchors if anchor in source.unavailable)
            for anchor in missing:
                run.state.record(
                    "labeling",
                    "labeler_source_image_unavailable",
                    anchors=(anchor,),
                    detail=source.unavailable[anchor],
                )
            if missing:
                unlabeled.append(family.question_id)
            else:
                items.append(_labeling_item(family.question_id, source, anchors))
        return LabelingRequest(job_id=run.job.job_id, items=tuple(items)), unlabeled

    async def _label_and_convert(
        self, run: _Run, manifest: ExamManifest, tasks: asyncio.TaskGroup
    ) -> None:
        started = time.monotonic()
        request, unlabeled = self._labeling_request(run, manifest)
        for question_id in unlabeled:
            run.kinds[question_id] = NativeExamItemKind.FREE_TEXT
        if unlabeled:
            self._dispatch(run, unlabeled, "wi-", tasks)

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
                    unlabeled.append(result.item_id)
                    continue
                run.kinds[result.item_id] = _KIND_OF_LABEL[result.label]
                run.first_pass[result.item_id] = (result.first_pass or result).probabilities
                labeled.append(result.item_id)
            self._dispatch(run, labeled, prefix, tasks)
            if unlabeled:
                tasks.create_task(self._unlabeled(run, unlabeled, f"{prefix}u", tasks))

        try:
            await self._labeler.label(request=request, on_results=settle)
        except ItemTypeLabelerError as error:
            run.state.record("labeling", error.code, detail=str(error.status_code or ""))
            run.state.fail_all_pending(_LABELING_REASON)
            return
        run.timed("labeling", started)

    def _dispatch(
        self, run: _Run, question_ids: list[str], prefix: str, tasks: asyncio.TaskGroup
    ) -> None:
        chosen = set(question_ids)
        families = tuple(f for f in run.families if f.question_id in chosen)
        for batch in pack_batches(
            families, run.kinds, families_per_batch=self._families_per_batch, prefix=prefix
        ):
            tasks.create_task(self._convert(run, batch, tasks))

    def _batch_state(self, run: _Run, batch: ConversionBatch) -> DocxBuildState:
        job = run.job
        return DocxBuildState(
            job.job_id,
            job.document_id,
            job.filename,
            job.source_sha256,
            job.chunks,
            claimable=batch.claims,
            context_anchors=batch.reads,
            allowed_kinds=batch.kinds,
            batch=batch.batch_id,
            keep_conflicts=any(qid in run.resent for qid in batch.question_ids),
            questions=tuple(f.question_anchors for f in run.families),
        )

    async def _convert(self, run: _Run, batch: ConversionBatch, tasks: asyncio.TaskGroup) -> None:
        started = time.monotonic()
        outcome = await self._converted(run, batch)
        run.timed(f"batch {batch.batch_id}", started)
        await self._deliver(run, batch, outcome, tasks)

    async def _unlabeled(
        self, run: _Run, question_ids: list[str], batch_id: str, tasks: asyncio.TaskGroup
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
        await self._deliver(run, batch, self._reviewed(run, batch, UNLABELED_REASON), tasks)

    async def _deliver(
        self, run: _Run, batch: ConversionBatch, outcome: BatchOutcome, tasks: asyncio.TaskGroup
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
                outcome = self._failed(run, batch, "batch_merge_failed", error)
                update = self._merged(run, batch, outcome)
            await self._progress.batch_ready(
                worker_id=run.job.worker_id, job_id=run.job.job_id, update=update
            )
        if outcome.conflicts:
            self._dispatch(run, list(outcome.conflicts), f"{batch.batch_id}c", tasks)

    async def _converted(self, run: _Run, batch: ConversionBatch) -> BatchOutcome:
        """The batch's admitted and contract-checked items, else its questions for review."""
        families = {f.question_id: f for f in run.families if f.question_id in batch.question_ids}
        try:
            outcome = await convert_batch(
                state=self._batch_state(run, batch),
                batch=batch,
                families=families,
                exchange=self._exchange,
                profile=self._profile,
            )
            with_confidence(outcome.state, run.families, run.confidence())
            validated(outcome.state)
        except Exception as error:
            # One batch's failure never fails the conversion (D25).
            logger.exception(
                "DOCX conversion batch failed", job_id=str(run.job.job_id), batch=batch.batch_id
            )
            return self._failed(run, batch, "batch_failed", error)
        return outcome

    def _failed(
        self, run: _Run, batch: ConversionBatch, code: str, error: Exception
    ) -> BatchOutcome:
        """Each of the batch's questions as one review item holding its source text."""
        outcome = self._reviewed(run, batch, _BATCH_FAILED_REASON)
        outcome.state.record("batch", code, detail=type(error).__name__)
        return outcome

    def _reviewed(self, run: _Run, batch: ConversionBatch, reason: str) -> BatchOutcome:
        state = self._batch_state(run, batch)
        state.review_questions(
            (run.own_anchors[qid] for qid in batch.question_ids),
            keys=frozenset(a for qid in batch.question_ids for a in run.key_anchors[qid]),
            contexts=run.context_anchors,
            title=run.title_anchors,
            reason=reason,
        )
        return BatchOutcome(state)

    def _merged(self, run: _Run, batch: ConversionBatch, outcome: BatchOutcome) -> ConversionUpdate:
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
        provisional = provisional_result(
            trial, families, frozenset(pending), governed_anchors(run.contexts, families)
        )
        update = conversion_update(provisional.document, families, filled, pending)
        run.state = trial
        run.families = families
        run.filled = list(filled)
        for qid, kind in outcome.conflicts.items():
            run.kinds[qid] = kind
            run.resent.add(qid)
        return update

    def _final(self, run: _Run, manifest: ExamManifest | None) -> DocxConversionOutcome:
        started = time.monotonic()
        result = run.state.result(governed_anchors(run.contexts, run.families))
        update = conversion_update(result.document, run.families, tuple(run.filled), ())
        checks = assembly_check(result.document, manifest, run.families, update) if manifest else ()
        run.timed("assembly", started)
        return DocxConversionOutcome(
            result=replace(result, events=(*result.events, *checks), timings=tuple(run.timings)),
            update=update,
        )
