"""Assemble shared native prompt bodies for the QTI import.

``qti_import`` owns package assembly, parents and notes and
``qti_import_leaf_items`` owns one leaf item's points and answer key; this
module owns only the projection from read prompt paragraphs, plain lines and
image ids to positioned native paragraphs.
"""

from __future__ import annotations

from collections.abc import Sequence

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiMatchEntry,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptSegment,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)


def paragraphs(
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    *,
    image_ids: Sequence[str],
    plain_lines: tuple[str, ...],
) -> tuple[NativeParagraph, ...]:
    if not paragraphs:
        return tuple(_plain_paragraph(line) for line in plain_lines)
    return tuple(
        NativeParagraph(
            heading_level=paragraph.heading_level,
            segments=tuple(_segment(segment, image_ids) for segment in paragraph.segments),
        )
        for paragraph in paragraphs
    )


def _segment(
    segment: ExamNetQtiPromptSegment,
    image_ids: Sequence[str],
) -> NativeTextSegment | NativeAssetSegment | NativeGapSegment:
    if isinstance(segment, ExamNetQtiPromptText):
        return NativeTextSegment(text=segment.text, marks=segment.marks)
    if isinstance(segment, ExamNetQtiPromptImage):
        return NativeAssetSegment(asset_id=image_ids[segment.image_index])
    return NativeGapSegment(gap_id=f"gap_{segment.gap_index + 1:03d}")


def _plain_paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(
        heading_level=None,
        segments=(NativeTextSegment(text=text, marks=()),),
    )


def label_body(
    choice: ExamNetQtiChoice | ExamNetQtiMatchEntry,
    *,
    image_ids: Sequence[str],
) -> tuple[NativeParagraph, ...]:
    if choice.body:
        return paragraphs(choice.body, image_ids=image_ids, plain_lines=())
    return (_plain_paragraph(choice.text),)
