"""Accepted items, chunk roles, observed failures and usage for one DOCX build."""

import copy
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from uuid import UUID

import structlog

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    NOTHING_GOVERNED,
    assemble_build_result,
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
    split_section_totals,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    title_without_answer_key,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError

logger = structlog.get_logger(__name__)

NO_ITEM_REASON = "AI-tolkningen gav ingen fråga eller rubrik för källstycket."


@dataclass(frozen=True)
class TypeConflict:
    """A question the converter reports, or produces, outside the batch's item kinds."""

    anchors: tuple[str, ...]
    kind: NativeExamItemKind


@dataclass
class DocxBuildState:
    """Freeze accepted items; every unclaimed chunk keeps the last reason it failed.

    ``chunks`` is always the whole document, because the opening heading, definitions and
    section totals are document-wide. A type batch claims only ``claimable`` anchors (None:
    every anchor), reads ``context_anchors`` as read-only instructions, and admits only
    ``allowed_kinds`` (None: every kind). ``questions`` holds each grouped question's own
    anchors, never its answer keys. ``governing`` holds the grouping's chunks that govern two
    or more questions; one no entry holds becomes its section parent's instruction (D40).
    """

    job_id: UUID
    document_id: UUID
    filename: str
    source_sha256: str
    chunks: tuple[DocxChunk, ...]
    claimable: frozenset[str] | None = None
    context_anchors: frozenset[str] = frozenset()
    allowed_kinds: frozenset[NativeExamItemKind] | None = None
    batch: str | None = None
    questions: tuple[tuple[str, ...], ...] = ()
    governing: frozenset[str] = frozenset()
    known_anchors: frozenset[str] = field(init=False, repr=False, compare=False)
    chunk_by_anchor: dict[str, DocxChunk] = field(init=False, repr=False, compare=False)
    question_by_anchor: dict[str, tuple[str, ...]] = field(init=False, repr=False, compare=False)
    accepted: list[tuple[NativeExamItem, tuple[str, ...]]] = field(default_factory=list)
    title: ProducedMetadata | None = None
    instructions: tuple[ProducedMetadata, ...] = ()
    key_anchors: set[str] = field(default_factory=set)
    claimed: set[str] = field(default_factory=set)
    reasons: dict[str, str] = field(default_factory=dict)
    conflicts: list[TypeConflict] = field(default_factory=list)
    keep_conflicts: bool = False
    kept_conflicts: set[str] = field(default_factory=set)
    events: list[DocxBuildEvent] = field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    input_complete: bool = True
    output_complete: bool = True

    def __post_init__(self) -> None:
        # Chunks are fixed for the state's lifetime, so the anchor index is built once.
        self.chunk_by_anchor = {chunk.anchor: chunk for chunk in self.chunks}
        self.known_anchors = frozenset(self.chunk_by_anchor)
        self.question_by_anchor = {a: own for own in self.questions for a in own}

    @property
    def owned(self) -> frozenset[str]:
        return self.known_anchors if self.claimable is None else self.claimable

    @property
    def pending(self) -> tuple[DocxChunk, ...]:
        owned = self.owned
        return tuple(
            chunk
            for chunk in self.chunks
            if chunk.anchor in owned and chunk.anchor not in self.claimed
        )

    def snapshot(self) -> "DocxBuildState":
        """A copy a trial merge may change without changing this state; items are frozen."""
        trial = copy.copy(self)
        trial.accepted = list(self.accepted)
        trial.key_anchors = set(self.key_anchors)
        trial.claimed = set(self.claimed)
        trial.reasons = dict(self.reasons)
        trial.conflicts = list(self.conflicts)
        trial.kept_conflicts = set(self.kept_conflicts)
        trial.events = list(self.events)
        return trial

    def printed(
        self, anchors: tuple[str, ...], reason: str, taken: set[str]
    ) -> tuple[NativeExamItem, tuple[str, ...]]:
        """The question ``anchors`` belong to as printed, facit included, as one review item.

        The item shows every own chunk of each grouped question ``anchors`` touch and every
        chunk in ``anchors``, in source order. It holds ``anchors`` plus the shown chunks no
        entry holds yet, which join ``taken``.
        """
        shown = set(anchors).union(*(self.question_by_anchor.get(a, ()) for a in anchors))
        extra = tuple(
            c.anchor
            for c in self.pending
            if c.anchor in shown and c.anchor not in anchors and c.anchor not in taken
        )
        taken.update(extra)
        item = review_source_item(tuple(c for c in self.chunks if c.anchor in shown), reason)
        return item, (*anchors, *extra)

    def review_questions(
        self,
        questions: Iterable[tuple[str, ...]],
        *,
        keys: frozenset[str],
        contexts: frozenset[str],
        title: frozenset[str],
        reason: str,
    ) -> None:
        """Rebuild an unconverted batch from its source alone.

        Each question with an unclaimed own chunk becomes one review item holding the source
        text of all its own chunks at the question's place. Answer-key chunks stay teacher
        notes, the grouped title stays the title, and shared section text and headings stay
        section text, each in its source wording.
        Every other pending chunk becomes a review item with ``reason``.
        """
        for anchors in questions:
            own = tuple(c.anchor for c in self.pending if c.anchor in anchors)
            if own:
                self.accepted.append(self.printed(own, reason, self.claimed))
                self.claimed.update(own)
        heading = tuple(c for c in self.pending if c.anchor in title)
        for chunk in self.pending:
            if chunk.anchor in keys:
                self.key_anchors.add(chunk.anchor)
            elif chunk.anchor not in title and (
                chunk.anchor in contexts or chunk.kind == "heading"
            ):
                section = ProducedMetadata(text=chunk.text, source_anchors=(chunk.anchor,))
                self.instructions = (*self.instructions, section)
            else:
                continue
            self.claimed.add(chunk.anchor)
        if heading and self.title is None:
            try:
                text = title_without_answer_key(" ".join(c.text for c in heading))
            except DomainError:
                text = ""
            if text:
                anchors = tuple(c.anchor for c in heading)
                self.title = ProducedMetadata(text=text, source_anchors=anchors)
                self.claimed.update(anchors)
        self.fail_all_pending(reason)

    def release(self, anchors: frozenset[str]) -> None:
        """Hand anchors back to the pipeline: this batch no longer owns or reports them."""
        self.claimable = self.owned - anchors
        self.accepted = [entry for entry in self.accepted if not anchors.intersection(entry[1])]
        self.claimed -= anchors
        for anchor in anchors:
            self.reasons.pop(anchor, None)

    def record(
        self,
        stage: str,
        code: str,
        *,
        item: int | None = None,
        anchors: tuple[str, ...] = (),
        detail: str = "",
    ) -> None:
        """Log and retain one failure; detail carries identifiers, never exam wording."""
        event = DocxBuildEvent.model_validate(
            {
                "stage": stage,
                "code": code,
                "batch": self.batch,
                "item": item,
                "anchors": anchors,
                "detail": detail,
            }
        )
        self.events.append(event)
        logger.warning("DOCX build failure observed", job_id=str(self.job_id), **event.as_json())

    def fail_chunks(self, anchors: tuple[str, ...] | set[str], reason: str) -> None:
        owned = self.owned
        for anchor in anchors:
            if anchor in owned and anchor not in self.claimed:
                self.reasons[anchor] = reason

    def fail_all_pending(self, reason: str) -> None:
        self.fail_chunks({chunk.anchor for chunk in self.pending}, reason)

    def record_usage(self, usage: StructuredLLMUsage) -> None:
        """Accumulate measured usage, retaining unknown totals as unknown."""
        if usage.prompt_tokens is not None and usage.prompt_tokens >= 0:
            self.input_tokens = (self.input_tokens or 0) + usage.prompt_tokens
        else:
            self.input_complete = False
        if usage.completion_tokens is not None and usage.completion_tokens >= 0:
            self.output_tokens = (self.output_tokens or 0) + usage.completion_tokens
        else:
            self.output_complete = False

    def result(
        self,
        governed: Mapping[str, frozenset[str]] = NOTHING_GOVERNED,
        questions: tuple[tuple[str, ...], ...] = (),
    ) -> DocxBuildResult:
        """Every chunk not built or used as metadata/facit becomes a review item, except a
        governing chunk, which becomes its section parent's instruction.

        ``governed`` maps each grouping instruction that governs two or more questions to the
        anchors those questions own; it decides which items the instruction is the parent of.
        ``questions`` holds each grouped question's own anchors; an instruction holding one
        stands only where it lands at that question (D42).

        A printed section total gives each question that prints no points of its own a
        share marked as estimated (D38, D6). A section's points line the split absorbs is
        metadata, never a review item.
        """
        points = split_section_totals(
            self.chunks,
            tuple(self.accepted),
            self.instructions,
            frozenset(chunk.anchor for chunk in self.pending),
        )
        review_reasons: dict[str, str] = {}
        for chunk in self.pending:
            if chunk.anchor in points.absorbed:
                continue
            if chunk.anchor in governed and chunk.text:
                # Assembly makes it its section parent's instruction (D40).
                review_reasons[chunk.anchor] = NO_ITEM_REASON
                self.record("fallback", "governing_instruction", anchors=(chunk.anchor,))
                continue
            reason = self.reasons.get(chunk.anchor, NO_ITEM_REASON)
            review_reasons[chunk.anchor] = reason
            self.record("fallback", "review_item", anchors=(chunk.anchor,), detail=reason)
        accepted = points.accepted
        result = assemble_build_result(
            document_id=self.document_id,
            filename=self.filename,
            source_sha256=self.source_sha256,
            chunks=self.chunks,
            accepted=accepted,
            review_reasons=review_reasons,
            key_anchors=frozenset(self.key_anchors),
            title=self.title,
            instructions=self.instructions,
            governed=governed,
            questions=questions,
            events=tuple(self.events),
            input_tokens=self.input_tokens if self.input_complete else None,
            output_tokens=self.output_tokens if self.output_complete else None,
        )
        for event in result.events[len(self.events) :]:
            logger.warning(
                "DOCX build failure observed", job_id=str(self.job_id), **event.as_json()
            )
        return result
