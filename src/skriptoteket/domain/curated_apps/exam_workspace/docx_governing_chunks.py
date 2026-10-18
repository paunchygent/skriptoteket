"""A chunk the grouping marks as governing several questions belongs to its section parent (D40).

When a converter reply lists such a chunk in an item's source anchors, the item gives the
chunk up: the anchor leaves the item, every body paragraph aligned to the chunk leaves the
item's body, and the chunk becomes an instruction, which section placement shows once, on the
parent. The per-paragraph source alignment decides which paragraphs are the chunk, never their
wording (TASK-SKRIPT-39-04-14). An item whose whole body is the chunk keeps it and the chunk is
reported. An item that held nothing but governing chunks is dropped. A governing chunk no entry
holds becomes an instruction built from its source text. No reply is rejected or resent.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    Accepted,
    AcceptedEntry,
    AlignedItem,
)


@dataclass(frozen=True)
class ReleasedChunks:
    """Items without governing chunks, the instructions including them, and kept chunks."""

    accepted: Accepted
    instructions: tuple[ProducedMetadata, ...]
    events: tuple[DocxBuildEvent, ...]


def _item_without(aligned: AlignedItem, anchor: str) -> AlignedItem | None:
    """The item without the body paragraphs aligned to ``anchor``; None when they are its
    whole body."""
    kept = [
        (paragraph, chunk)
        for paragraph, chunk in zip(aligned.item.body, aligned.chunks, strict=True)
        if chunk != anchor
    ]
    if not kept:
        return None
    body = tuple(paragraph for paragraph, _ in kept)
    return AlignedItem(
        aligned.item.model_copy(update={"body": body}), tuple(chunk for _, chunk in kept)
    )


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
    kept: list[AcceptedEntry] = []
    for aligned, anchors in accepted:
        governing = [a for a in anchors if a in governed]
        if not governing:
            kept.append((aligned, anchors))
            continue
        for anchor in governing:
            without = _item_without(aligned, anchor)
            if without is None:
                events.append(
                    DocxBuildEvent(
                        stage="assembly",
                        code="governing_text_kept",
                        anchors=(anchor,),
                        detail=aligned.item.source_anchor or "",
                    )
                )
            else:
                aligned = without
            if anchor not in listed and anchor not in released:
                released.append(anchor)
        own = tuple(a for a in anchors if a not in governed)
        if own:
            first = min(own, key=positions.__getitem__)
            item = aligned.item.model_copy(update={"source_anchor": first})
            kept.append((replace(aligned, item=item), own))
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
