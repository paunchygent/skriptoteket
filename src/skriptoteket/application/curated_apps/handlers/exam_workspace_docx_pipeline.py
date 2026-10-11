"""Type-batched parallel DOCX conversion (TASK-SKRIPT-39-05-04 steps 1-4, D25, D29).

One grouping call maps the questions, one labeling call types them, and type batches
convert concurrently in two waves: questions the first labeling pass accepts convert at
once; each question the second pass decides converts as soon as its label arrives.
Each admitted batch reaches the progress port as a provisional document; the final
document is assembled in source order and checked against the grouping.

An unresolved or unsupported label converts as free text (D23). The strict schema is the
only gate on a batch response. A family the converter reports as a type conflict is resent
with the reported kind, the only resend. A family that still conflicts in its resend is
kept as converted and carries the type-check mark: its review confidence stays below the
acceptance threshold. Chunks no batch converts become review items, and a batch that raises
leaves only its own questions as review items holding their source text.
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
    merge_batch,
    provisional_result,
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
    question_source,
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
from skriptoteket.protocols.exam_workspace import DocxExamChunkerProtocol
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
    ItemTypeLabel.UNRESOLVED: NativeExamItemKind.FREE_TEXT,
}
_DISABLED_REASON = "AI-tolkning är avstängd. Kontrollera källtexten manuellt."
_LABELING_REASON = "Frågetyperna kunde inte avgöras. Kontrollera källtexten manuellt."
_BATCH_FAILED_REASON = "Frågan kunde inte tolkas. Kontrollera källtexten manuellt."

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


class DocxConversionPipeline:
    """Group, label and convert type batches concurrently into one native exam."""

    def __init__(
        self,
        *,
        grouper: ExamGrouperProtocol,
        labeler: ItemTypeLabelerProtocol,
        labeler_chunker: DocxExamChunkerProtocol,
        exchange: DocxBuildRoundExchange,
        profile: StructuredLLMProviderProfile,
        progress: DocxConversionProgressProtocol,
        uow: SerializedUnitOfWork,
        families_per_batch: int,
        enabled: bool,
    ) -> None:
        self._grouper = grouper
        self._labeler = labeler
        self._labeler_chunker = labeler_chunker
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

    def _labeling_request(self, run: _Run, manifest: ExamManifest) -> LabelingRequest:
        """Each question's faithful source markdown (D14); plain chunk text when the source
        holds content markdown cannot carry, until image input exists."""
        try:
            source = self._labeler_chunker.chunk(content=run.job.source_docx)
        except ValueError:
            run.state.record("labeling", "labeler_source_plain_text")
            source = run.job.chunks
        return LabelingRequest(
            job_id=run.job.job_id,
            items=tuple(
                LabelingItem(
                    item_id=f.question_id,
                    source_text=question_source(manifest, source, f.question_id),
                )
                for f in run.families
            ),
        )

    async def _label_and_convert(
        self, run: _Run, manifest: ExamManifest, tasks: asyncio.TaskGroup
    ) -> None:
        started = time.monotonic()

        def settle(results: tuple[ItemTypeLabelResult, ...]) -> None:
            for result in results:
                run.kinds[result.item_id] = _KIND_OF_LABEL[result.label]
                run.first_pass[result.item_id] = (result.first_pass or result).probabilities
            if results and results[0].decided_by is LabelPass.FIRST:
                run.timed("labeling_first_pass", started)
                self._dispatch(run, [r.item_id for r in results], "w1-", tasks)
            elif results:
                # Each second-pass label converts at once; a per-dispatch number keeps
                # every second-wave batch id unique.
                run.second_wave_dispatches += 1
                prefix = f"w2-{run.second_wave_dispatches:02d}-"
                self._dispatch(run, [r.item_id for r in results], prefix, tasks)

        try:
            await self._labeler.label(
                request=self._labeling_request(run, manifest), on_results=settle
            )
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
        )

    async def _convert(self, run: _Run, batch: ConversionBatch, tasks: asyncio.TaskGroup) -> None:
        started = time.monotonic()
        job = run.job
        families = {f.question_id: f for f in run.families if f.question_id in batch.question_ids}
        try:
            outcome = await convert_batch(
                state=self._batch_state(run, batch),
                batch=batch,
                families=families,
                exchange=self._exchange,
                profile=self._profile,
            )
        except Exception as error:
            # One batch's failure never fails the conversion (D25): its own questions become
            # review items holding their source text, and every other batch's result stays.
            logger.exception(
                "DOCX conversion batch failed", job_id=str(job.job_id), batch=batch.batch_id
            )
            outcome = BatchOutcome(self._batch_state(run, batch))
            outcome.state.record("batch", "batch_failed", detail=type(error).__name__)
            outcome.state.fail_all_pending(_BATCH_FAILED_REASON)
        state = outcome.state
        resend = list(outcome.conflicts)
        run.families = tuple(
            replace(f, claims=outcome.released[f.question_id])
            if f.question_id in outcome.released
            else f
            for f in run.families
        )
        for qid, kind in outcome.conflicts.items():
            run.kinds[qid] = kind
            run.resent.add(qid)
        with_confidence(state, run.families, run.confidence())
        run.timed(f"batch {batch.batch_id}", started)
        async with self._uow.lock:
            merge_batch(run.state, state, run.title_anchors)
            run.filled.extend(qid for qid in batch.question_ids if qid not in outcome.conflicts)
            provisional = provisional_result(run.state, run.families, frozenset(run.pending))
            await self._progress.batch_ready(
                worker_id=job.worker_id,
                job_id=job.job_id,
                update=conversion_update(
                    provisional.document, run.families, tuple(run.filled), run.pending
                ),
            )
        if resend:
            self._dispatch(run, resend, f"{batch.batch_id}c", tasks)

    def _final(self, run: _Run, manifest: ExamManifest | None) -> DocxConversionOutcome:
        started = time.monotonic()
        result = run.state.result()
        update = conversion_update(result.document, run.families, tuple(run.filled), ())
        checks = assembly_check(result.document, manifest, run.families, update) if manifest else ()
        run.timed("assembly", started)
        return DocxConversionOutcome(
            result=replace(result, events=(*result.events, *checks), timings=tuple(run.timings)),
            update=update,
        )
