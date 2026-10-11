"""Accepted items, chunk roles, observed failures and usage for one DOCX build."""

from dataclasses import dataclass, field
from uuid import UUID

import structlog

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
    split_section_totals,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamItemKind,
)

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
    ``allowed_kinds`` (None: every kind).
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
    known_anchors: frozenset[str] = field(init=False, repr=False, compare=False)
    chunk_by_anchor: dict[str, DocxChunk] = field(init=False, repr=False, compare=False)
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

    def result(self) -> DocxBuildResult:
        """Every chunk not built or used as metadata/facit becomes a review item.

        A printed section total that cannot be split equally leaves its items without
        points, which blocks export until a teacher sets them.
        """
        review_reasons: dict[str, str] = {}
        for chunk in self.pending:
            reason = self.reasons.get(chunk.anchor, NO_ITEM_REASON)
            review_reasons[chunk.anchor] = reason
            self.record("fallback", "review_item", anchors=(chunk.anchor,), detail=reason)
        accepted, unsplit = split_section_totals(
            self.chunks, tuple(self.accepted), self.instructions, frozenset(review_reasons)
        )
        for anchor in unsplit:
            self.record("fallback", "section_points_unsplit", anchors=(anchor,))
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
            events=tuple(self.events),
            input_tokens=self.input_tokens if self.input_complete else None,
            output_tokens=self.output_tokens if self.output_complete else None,
        )
        for event in result.events[len(self.events) :]:
            logger.warning(
                "DOCX build failure observed", job_id=str(self.job_id), **event.as_json()
            )
        return result
