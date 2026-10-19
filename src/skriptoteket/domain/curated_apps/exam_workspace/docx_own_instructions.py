"""A question's own chunk a reply lists as an instruction stands only at its question (D42).

The instruction stands when section placement puts it at that question: in the body of an
item that holds the question's other own chunks, or on a parent that holds such an item. A
chunk whose instruction lands anywhere else, such as the exam-wide instructions or another
section, goes back to its question's item. A converted item no body paragraph of which is aligned
to the chunk holds it under the check mark that shows left-out chunks as printed (D41, D4); a
review item already prints every own chunk of its question. The rest of the instruction keeps the
source text of its other chunks. A chunk the grouping marks as governing belongs to its
section parent (D40) and is never sent back. The check mark itself is decided later, on
the placed item, for the recorded anchors neither its body nor its parent shows
(TASK-SKRIPT-39-04-19).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    Accepted,
    AlignedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    answer_line,
    blank_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

LEFT_OUT_REASON = (
    "Delar av källtexten saknas i den konverterade frågan – kontrollera mot källan. "
    "Källtext som saknas:"
)
DRAWING_SHOWN = "[Bild utan text]"


@dataclass(frozen=True)
class ReturnedChunks:
    """Items holding the chunks sent back, the instructions without them, and what moved."""

    accepted: Accepted
    instructions: tuple[ProducedMetadata, ...]
    events: tuple[DocxBuildEvent, ...]


def left_out_chunks(aligned: AlignedItem, chunks: Iterable[DocxChunk]) -> tuple[DocxChunk, ...]:
    """The chunks no body paragraph, choice or matching entry of the item is aligned to (D4):
    the alignment, never the reply's wording, says what the item shows. A source answer or
    facit line is the item's key, never left-out text (TASK-SKRIPT-39-04-14); a blank answer
    line is the response space."""
    return tuple(
        chunk
        for chunk in chunks
        if not aligned.shows(chunk.anchor)
        and chunk.anchor not in aligned.entry_chunks
        and not answer_line(chunk.text)
        and not blank_line(chunk.text)
    )


def with_left_out_mark(item: NativeExamItem, chunks: Sequence[DocxChunk]) -> NativeExamItem:
    """The item under the check mark that shows ``chunks`` as printed (D41)."""
    texts = tuple(c.text or DRAWING_SHOWN for c in chunks if c.text or c.kind == "drawing")
    reasons = item.review.reasons
    heading = () if LEFT_OUT_REASON in reasons else (LEFT_OUT_REASON,)
    shown = (*reasons, *heading, *texts)
    review = item.review.model_copy(
        update={"state": NativeItemReviewState.REVIEW_REQUIRED, "reasons": shown}
    )
    return item.model_copy(update={"review": review})


def with_placed_left_out_mark(
    aligned: AlignedItem, chunks: Sequence[DocxChunk], placed: frozenset[str]
) -> AlignedItem:
    """The item under the check mark for the own chunks it leaves out and still misses.

    Only the anchors of ``aligned.left_out`` that no placed parent carries still count, in
    source order; the alignment, never the reply's wording, says what the item shows. A
    source item keeps its review as it stands (TASK-SKRIPT-39-04-19 D2).
    """
    if aligned.item.review.parse_origin is not NativeParseOrigin.LLM_PARSED:
        return aligned
    missing = left_out_chunks(
        aligned,
        [
            chunk
            for chunk in chunks
            if chunk.anchor in aligned.left_out and chunk.anchor not in placed
        ],
    )
    if not missing:
        return aligned
    return replace(aligned, item=with_left_out_mark(aligned.item, missing))


def _owner(accepted: Accepted, own: frozenset[str]) -> int | None:
    """The converted item holding the question's own chunks, else any item holding them."""
    holding = [k for k, (_, anchors) in enumerate(accepted) if own.intersection(anchors)]
    converted = [
        k
        for k in holding
        if accepted[k][0].item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    ]
    return next(iter(converted or holding), None)


def return_misplaced_own_chunks(
    chunks: tuple[DocxChunk, ...],
    accepted: Accepted,
    instructions: tuple[ProducedMetadata, ...],
    landed: Mapping[int, frozenset[str]],
    questions: tuple[tuple[str, ...], ...],
    governed: Mapping[str, frozenset[str]],
) -> ReturnedChunks | None:
    """Send each own chunk whose instruction lands away from its question back to it.

    ``landed`` maps each placed instruction's index to the anchors of the items it lands at,
    in their bodies or under their parent. None when every own chunk's instruction stands.
    """
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    question_of = {a: frozenset(own) for own in questions for a in own if a not in governed}
    back: dict[int, list[str]] = {}
    kept: list[ProducedMetadata] = []
    for origin, instruction in enumerate(instructions):
        at = landed.get(origin, frozenset())
        moved = []
        for anchor in instruction.source_anchors:
            own = question_of.get(anchor)
            if own is None or at.intersection(own):
                continue
            owner = _owner(accepted, own)
            if owner is not None:
                back.setdefault(owner, []).append(anchor)
                moved.append(anchor)
        rest = tuple(a for a in instruction.source_anchors if a not in moved)
        if not moved:
            kept.append(instruction)
        elif rest:
            # The reply's text may hold the moved chunks' wording; the rest shows its source text.
            text = "\n".join(by_anchor[a].text for a in rest)
            kept.append(instruction.model_copy(update={"text": text, "source_anchors": rest}))
    if not back:
        return None
    positions = {chunk.anchor: i for i, chunk in enumerate(chunks)}
    updated = list(accepted)
    events = []
    for k, anchors in back.items():
        aligned, held = updated[k]
        item = aligned.item
        ordered = sorted(anchors, key=positions.__getitem__)
        if item.review.parse_origin is NativeParseOrigin.LLM_PARSED and (
            missing := left_out_chunks(aligned, [by_anchor[a] for a in ordered])
        ):
            aligned = replace(
                aligned, left_out=aligned.left_out | {chunk.anchor for chunk in missing}
            )
        updated[k] = (aligned, (*held, *ordered))
        events.append(
            DocxBuildEvent(
                stage="assembly",
                code="own_instruction_returned",
                anchors=tuple(ordered),
                detail=item.source_anchor or "",
            )
        )
    return ReturnedChunks(tuple(updated), tuple(kept), tuple(events))
