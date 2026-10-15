"""A chunk the grouping marks as governing several questions belongs to its section parent (D40).

When a converter reply lists such a chunk in an item's source anchors, the item gives the
chunk up: the anchor leaves the item, the chunk's wording leaves the item's body
where the item prints it as the chunk's source text, and the chunk becomes an instruction,
which section placement shows once, on the parent. Wording is removed only where it matches
the chunk's source text after whitespace normalization and stands as whole lines, or at the
start or end of a paragraph text; wording found anywhere else is kept and reported.
An item that held nothing but governing chunks is dropped. A governing chunk no entry holds
becomes an instruction built from its source text. No reply is rejected or resent.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)

Accepted = tuple[tuple[NativeExamItem, tuple[str, ...]], ...]


@dataclass(frozen=True)
class ReleasedChunks:
    """Items without governing chunks, the instructions including them, and kept wording."""

    accepted: Accepted
    instructions: tuple[ProducedMetadata, ...]
    events: tuple[DocxBuildEvent, ...]


def _squash(text: str) -> str:
    return " ".join(text.split())


def _words(text: str) -> str:
    return r"\s+".join(re.escape(word) for word in text.split())


def _without_lines(text: str, wanted: list[str]) -> str | None:
    """The text without the contiguous whole lines equal to ``wanted``; None if absent."""
    raw = text.split("\n")
    shown = [(k, _squash(line)) for k, line in enumerate(raw) if line.strip()]
    for start in range(len(shown) - len(wanted) + 1):
        if [line for _, line in shown[start : start + len(wanted)]] == wanted:
            dropped = {k for k, _ in shown[start : start + len(wanted)]}
            return "\n".join(line for k, line in enumerate(raw) if k not in dropped).strip("\n")
    return None


def _without_edge(text: str, chunk_text: str) -> str | None:
    """The text without the chunk's wording at its start or end, keeping the spacing on the
    other side; None if the wording stands elsewhere."""
    words = _words(chunk_text)
    start = re.match(rf"\s*{words}(?=\s|$)\s*", text)
    if start is not None:
        return text[start.end() :]
    end = re.search(rf"(?:^|\s+){words}\s*$", text)
    return None if end is None else text[: end.start()]


def _removed(text: str, chunk_text: str) -> str | None:
    """The text without the chunk's wording, or None when no faithful removal exists."""
    lines = [line for raw in chunk_text.splitlines() if (line := _squash(raw))]
    without = _without_lines(text, lines)
    if without is None:
        without = _without_edge(text, chunk_text)
    return None if without is None else without.strip()


def _paragraph_without(
    paragraph: NativeParagraph, chunk_text: str
) -> tuple[NativeParagraph, ...] | None:
    """The paragraph without the chunk's wording, as nothing when only that wording remained;
    None when the paragraph does not print it where it can be removed."""
    segments = paragraph.segments
    if all(isinstance(s, NativeTextSegment) for s in segments):
        joined = "".join(s.text for s in segments if isinstance(s, NativeTextSegment))
        rest = _removed(joined, chunk_text)
        if rest is None:
            return None
        if not rest:
            return ()
        kept_text: list[NativeSegment] = []
        cursor = 0
        # Removal can leave disjoint whole lines. Slice the original runs rather
        # than flattening their marks into a new unformatted text segment.
        for line in rest.splitlines(keepends=True):
            start = joined.find(line, cursor)
            if start < 0:
                return None
            end = start + len(line)
            offset = 0
            for segment in segments:
                if isinstance(segment, NativeTextSegment):
                    left, right = max(start, offset), min(end, offset + len(segment.text))
                    if left < right:
                        kept_text.append(
                            segment.model_copy(
                                update={"text": segment.text[left - offset : right - offset]}
                            )
                        )
                    offset += len(segment.text)
            cursor = end
        return (paragraph.model_copy(update={"segments": tuple(kept_text)}),)
    for at in (0, len(segments) - 1):
        segment = segments[at]
        if not isinstance(segment, NativeTextSegment):
            continue
        rest = _without_edge(segment.text, chunk_text)
        if rest is None:
            continue
        kept: list[NativeSegment] = list(segments)
        if rest.strip():
            kept[at] = segment.model_copy(update={"text": rest})
        else:
            del kept[at]
        return (paragraph.model_copy(update={"segments": tuple(kept)}),)
    return None


def _item_without(item: NativeExamItem, chunk_text: str) -> NativeExamItem | None:
    """The item without the chunk's wording; the item itself when it does not print it; None
    when it prints it where no faithful removal exists, or where removing it leaves no body."""
    for k, paragraph in enumerate(item.body):
        without = _paragraph_without(paragraph, chunk_text)
        if without is not None:
            body = (*item.body[:k], *without, *item.body[k + 1 :])
            return item.model_copy(update={"body": body}) if body else None
    printed = _squash(" ".join(item.plain_text_lines()))
    return None if _squash(chunk_text) in printed else item


def release_governing_chunks(
    chunks: tuple[DocxChunk, ...],
    accepted: Accepted,
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
) -> ReleasedChunks:
    """Take every governing chunk out of the items that list it and make it an instruction."""
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    positions = {chunk.anchor: i for i, chunk in enumerate(chunks)}
    listed = {anchor for instruction in instructions for anchor in instruction.source_anchors}
    released: list[str] = []
    events: list[DocxBuildEvent] = []
    kept: list[tuple[NativeExamItem, tuple[str, ...]]] = []
    for item, anchors in accepted:
        governing = [a for a in anchors if a in governed]
        if not governing:
            kept.append((item, anchors))
            continue
        for anchor in governing:
            without = _item_without(item, by_anchor[anchor].text)
            if without is None:
                events.append(
                    DocxBuildEvent(
                        stage="assembly",
                        code="governing_text_kept",
                        anchors=(anchor,),
                        detail=item.source_anchor or "",
                    )
                )
            else:
                item = without
            if anchor not in listed and anchor not in released:
                released.append(anchor)
        own = tuple(a for a in anchors if a not in governed)
        if own:
            first = min(own, key=positions.__getitem__)
            kept.append((item.model_copy(update={"source_anchor": first}), own))
    added = tuple(
        ProducedMetadata(text=by_anchor[anchor].text, source_anchors=(anchor,))
        for anchor in released
    )
    return ReleasedChunks(tuple(kept), (*instructions, *added), tuple(events))


def unclaimed_governing(
    chunks: tuple[DocxChunk, ...],
    review_reasons: Mapping[str, str],
    governed: Mapping[str, frozenset[str]],
) -> tuple[tuple[ProducedMetadata, ...], dict[str, str]]:
    """Each governing chunk no entry holds as an instruction of its source text, and the
    review reasons of every other unbuilt chunk."""
    moved = {
        chunk.anchor: chunk.text
        for chunk in chunks
        if chunk.anchor in review_reasons and chunk.anchor in governed and chunk.text
    }
    instructions = tuple(
        ProducedMetadata(text=text, source_anchors=(anchor,)) for anchor, text in moved.items()
    )
    return instructions, {a: r for a, r in review_reasons.items() if a not in moved}
