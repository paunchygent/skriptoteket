"""Shared placement builders for the heading-placement tests.

The question-heading and section-heading tests place the same chunk and item
shapes; the grouped checks read the placed items and parents either way.
"""

from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    Placed,
    SectionInstructions,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

_NOTHING_GOVERNED: MappingProxyType[str, frozenset[str]] = MappingProxyType({})


def _chunk(anchor: str, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind=kind, text=text, marked_text=text)


def _item(text: str) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        writing_lines=8,
        body=(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
    )


def _aligned(item: NativeExamItem, *chunks: str | None) -> AlignedItem:
    """The item with the source chunk each body paragraph shows."""
    return AlignedItem(item, chunks, frozenset())


def _place(
    chunks: tuple[DocxChunk, ...],
    placed: list[Placed],
    instructions: tuple[ProducedMetadata, ...] = (),
    title_anchors: frozenset[str] = frozenset(),
    governed: MappingProxyType[str, frozenset[str]] = _NOTHING_GOVERNED,
) -> SectionInstructions:
    return place_section_instructions(
        chunks,
        placed,
        instructions,
        governed,
        title_anchors,
    )


def _ordered(chunks: tuple[DocxChunk, ...], *anchors: str) -> list[Placed]:
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    return [
        (positions[anchor], (anchor,), _aligned(_item(f"Frågetext {anchor}"), anchor))
        for anchor in anchors
    ]
