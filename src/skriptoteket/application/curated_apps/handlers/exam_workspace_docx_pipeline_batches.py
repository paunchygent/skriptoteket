"""Batch admission states and review outcomes for the DOCX conversion pipeline (D25, D29).

One dispatched type batch becomes one or more admission parts. A part whose families claim
or read a chunk holding a picture the chunker could not turn into an image depends on that
unavailable source and is held for teacher review with the picture's reason; every other
family in the same batch converts. A missing picture shared by several families therefore
gates each of them, and no one else. The dispatched batch is its own only part when no
family, or every family, depends on an unavailable picture.

A converting part admits the batch's response, marks conflicts kept for a type check, and
checks every item against the native contract; a failure leaves that part's own questions
holding their source text for review and never fails the conversion.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    governed_anchors,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import missing_picture_reasons
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

_BATCH_FAILED_REASON = "Frågan kunde inte tolkas. Kontrollera källtexten manuellt."


@dataclass(frozen=True)
class BatchPart:
    """One admission unit of a dispatched batch.

    ``missing`` holds every chunk with an unavailable picture that the part's families
    claim or read; a part with none converts, and one with any is held for review.
    """

    batch: ConversionBatch
    missing: tuple[DocxChunk, ...] = ()

    @property
    def missing_reason(self) -> str:
        """One named Swedish reason per unavailable picture, in source order."""
        return " ".join(missing_picture_reasons(self.missing))


def source_parts(run: DocxConversionRun, batch: ConversionBatch) -> tuple[BatchPart, ...]:
    """The batch split by the unavailable pictures its families depend on.

    A family depends on an unavailable picture when one of its claimed or read chunks
    holds it. Such a family is held for review while every family that does not depend
    on it converts; a picture shared by several families gates all of them together. The
    dispatched batch is its own only part when no family, or every family, depends on an
    unavailable picture.
    """
    families = tuple(f for f in run.families if f.question_id in batch.question_ids)
    missing = {f.question_id: _missing_chunks(run, f.claims | f.reads) for f in families}
    gated = tuple(f for f in families if missing[f.question_id])
    if not gated:
        return (BatchPart(batch),)
    reasons = _missing_chunks(run, frozenset().union(*(f.claims | f.reads for f in gated)))
    if len(gated) == len(families):
        return (BatchPart(batch, reasons),)
    converted = tuple(f for f in families if not missing[f.question_id])
    return (
        BatchPart(_subset(batch, gated), reasons),
        BatchPart(_subset(batch, converted)),
    )


def source_reviewed(run: DocxConversionRun, part: BatchPart) -> BatchOutcome:
    """The part's families held for review, recording the unavailable pictures that did it."""
    outcome = reviewed(run, part.batch, part.missing_reason)
    outcome.state.record(
        "batch",
        "source_picture_missing",
        anchors=tuple(chunk.anchor for chunk in part.missing),
        detail=part.missing_reason,
    )
    return outcome


def batch_state(run: DocxConversionRun, batch: ConversionBatch) -> DocxBuildState:
    """The batch's admission state: its claims, its read-only context and its allowed kinds."""
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
        governing=frozenset(governed_anchors(run.contexts, run.families)),
        grouped_keys=frozenset(a for anchors in run.key_anchors.values() for a in anchors),
    )


def failed(
    run: DocxConversionRun, batch: ConversionBatch, code: str, error: Exception
) -> BatchOutcome:
    """Each of the batch's questions as one review item holding its source text."""
    outcome = reviewed(run, batch, _BATCH_FAILED_REASON)
    outcome.state.record("batch", code, detail=type(error).__name__)
    return outcome


def reviewed(run: DocxConversionRun, batch: ConversionBatch, reason: str) -> BatchOutcome:
    """Every question of the batch rebuilt from its source alone, with ``reason``."""
    state = batch_state(run, batch)
    state.review_questions(
        (run.own_anchors[qid] for qid in batch.question_ids),
        keys=frozenset(a for qid in batch.question_ids for a in run.key_anchors[qid]),
        contexts=run.context_anchors,
        title=run.title_anchors,
        reason=reason,
    )
    return BatchOutcome(state)


def _missing_chunks(run: DocxConversionRun, anchors: frozenset[str]) -> tuple[DocxChunk, ...]:
    """The chunks among ``anchors`` holding a picture no image could be made of."""
    return tuple(
        chunk for chunk in run.job.chunks if chunk.anchor in anchors and chunk.missing_images
    )


def _subset(batch: ConversionBatch, families: tuple[QuestionFamily, ...]) -> ConversionBatch:
    """The batch's kinds and id narrowed to ``families``, with their own claims and context."""
    claims = frozenset().union(*(f.claims for f in families))
    reads = frozenset().union(*(f.reads for f in families)) - claims
    return ConversionBatch(
        batch_id=batch.batch_id,
        kinds=batch.kinds,
        question_ids=tuple(f.question_id for f in families),
        claims=claims,
        reads=reads,
    )
