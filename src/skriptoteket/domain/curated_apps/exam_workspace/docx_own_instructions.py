"""A question's own chunk a reply lists as an instruction stands only at its question (D42).

The instruction stands when section placement puts it at that question: in the body of an
item that holds the question's other own chunks, or on a parent that holds such an item. A
chunk whose instruction lands anywhere else, such as the exam-wide instructions or another
section, goes back to its question's item. A converted item that lacks the chunk's wording holds
it under the check mark that shows left-out chunks as printed (D41, D4); a review item already
prints every own chunk of its question. The rest of the instruction keeps the
source text of its other chunks. A chunk the grouping marks as governing belongs to its
section parent (D40) and is never sent back.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeGapSegment,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
)

LEFT_OUT_REASON = (
    "Delar av källtexten saknas i den konverterade frågan – kontrollera mot källan. "
    "Källtext som saknas:"
)
DRAWING_SHOWN = "[Bild utan text]"

Accepted = tuple[tuple[NativeExamItem, tuple[str, ...]], ...]


@dataclass(frozen=True)
class ReturnedChunks:
    """Items holding the chunks sent back, the instructions without them, and what moved."""

    accepted: Accepted
    instructions: tuple[ProducedMetadata, ...]
    events: tuple[DocxBuildEvent, ...]


# A unit's own number or letter, such as "3.", "b)" or "Fråga 3:", and an answer or facit line.
_NUMBERING = re.compile(
    r"^\s*(?:(?:fråga|uppgift|question|task)\s+\d+[a-z]?\s*[.):]?|\d+[a-z]?\s*[.):]|[a-z]\s*[.)])\s*",
    re.IGNORECASE,
)
_ANSWER_LINE = re.compile(
    r"^\s*\(?\s*(?:(?:correct|right|rätt|korrekt)\s+)?"
    r"(?:svar|svarsexempel|facit|answers?(?:\s+key)?|key)\s*:",
    re.IGNORECASE,
)
# Where a printed line holds several units: a table cell boundary or an inline option letter.
_UNIT_BREAK = re.compile(r"\s\|\s|\s(?=[a-z]\s*[.)]\s)", re.IGNORECASE)
# Words, numbers and single letters, and the symbols that carry mathematical content.
_TOKEN = re.compile(r"[^\W_]+|[+−=<>≤≥×÷*/^%]")
# A dash in front of a word, as in "e-post" or "frågan – tolkningen", is punctuation; every
# other dash, as in "x - y", "x=-7" or "-(x + y)", is a minus.
_WORD_DASH = re.compile(r"[-−–—](?=\s*[^\W\d_]{2})")
_DASH = re.compile(r"[-−–—]")

Gap = tuple[tuple[str, ...], ...]
# A picture in the body: no printed unit reads across it.
_PICTURE = ""
Stream = tuple[str | Gap, ...]


def _tokens(text: str | None) -> tuple[str, ...]:
    words = _DASH.sub(" − ", _WORD_DASH.sub(" ", text or ""))
    return tuple(token.casefold() for token in _TOKEN.findall(words))


def _units(chunk: DocxChunk) -> tuple[tuple[str, ...], ...]:
    """The chunk's printed units in order, without points labels, numbering and facit lines."""
    units = []
    for line in chunk.text.splitlines():
        for part in _UNIT_BREAK.split(POINT_LABEL.sub(" ", line)):
            unit = _NUMBERING.sub("", part)
            if not _ANSWER_LINE.match(unit) and (tokens := _tokens(unit)):
                units.append(tokens)
    return tuple(units)


def _streams(item: NativeExamItem) -> tuple[Stream, ...]:
    """The item's texts in order; a gap reads as nothing or as one of its accepted values."""
    gaps = {gap.gap_id: tuple(_tokens(value) for value in gap.accepted_values) for gap in item.gaps}
    body: list[str | Gap] = []
    for paragraph in item.body:
        run = ""  # adjacent text segments read as one text, so a word may span them
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                run += segment.text
                continue
            body.extend(_tokens(run))
            run = ""
            if isinstance(segment, NativeGapSegment):
                body.append(gaps.get(segment.gap_id, ()))
            else:
                body.append(_PICTURE)
        body.extend(_tokens(run))
    texts = [
        item.title,
        item.marking_guide,
        *(value for gap in item.gaps for value in gap.accepted_values),
        *(choice.text for choice in item.choices),
        *(entry.text for entry in item.match_left),
        *(entry.text for entry in item.match_right),
    ]
    return (tuple(body), (*_tokens(item.title), *body), *(_tokens(text) for text in texts))


def _occurs(unit: tuple[str, ...], stream: Stream) -> bool:
    """Whether ``unit`` reads in order, without a break, somewhere in ``stream``."""
    matched: set[int] = set()
    for token in stream:
        matched.add(0)
        if isinstance(token, tuple):
            matched |= {
                k + len(value)
                for k in matched
                for value in token
                if value and unit[k : k + len(value)] == value
            }
        else:
            matched = {k + 1 for k in matched if k < len(unit) and unit[k] == token}
        if len(unit) in matched:
            return True
    return False


def wording_left_out(item: NativeExamItem, chunks: Iterable[DocxChunk]) -> tuple[DocxChunk, ...]:
    """The chunks with a unit the item does not read in order (D4); a drawing is never wording
    the item holds."""
    streams = _streams(item)
    return tuple(
        chunk
        for chunk in chunks
        if chunk.kind == "drawing"
        or not all(any(_occurs(unit, s) for s in streams) for unit in _units(chunk))
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


def _owner(accepted: Accepted, own: frozenset[str]) -> int | None:
    """The converted item holding the question's own chunks, else any item holding them."""
    holding = [k for k, (_, anchors) in enumerate(accepted) if own.intersection(anchors)]
    converted = [
        k for k in holding if accepted[k][0].review.parse_origin is NativeParseOrigin.LLM_PARSED
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
        item, held = updated[k]
        ordered = sorted(anchors, key=positions.__getitem__)
        if item.review.parse_origin is NativeParseOrigin.LLM_PARSED and (
            missing := wording_left_out(item, [by_anchor[a] for a in ordered])
        ):
            item = with_left_out_mark(item, missing)
        updated[k] = (item, (*held, *ordered))
        events.append(
            DocxBuildEvent(
                stage="assembly",
                code="own_instruction_returned",
                anchors=tuple(ordered),
                detail=item.source_anchor or "",
            )
        )
    return ReturnedChunks(tuple(updated), tuple(kept), tuple(events))
