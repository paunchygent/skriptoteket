"""The native exam document body: paragraphs of text, gap and asset segments.

Purpose:
    Hold the one body representation every native exam item uses (ADR-SKRIPT-0091,
    ST-SKRIPT-39-04 S1-S5): paragraphs of text, inline gaps and picture references. The
    document model and the parent/instruction model both read a body, so the segments live
    here instead of either importer. ``native_exam_document`` re-exports every name here.

Formatting:
    A text run carries the source document's marks and a paragraph carries its
    heading level, both decided by code from the source runs (TASK-SKRIPT-39-09-08).
    The DOCX lane casts reader values to ``NativeTextMark`` and
    ``Literal[1, 2, 3] | None`` at this boundary; the models require both fields so a
    producer can never save an unformatted body by accident.
    A reverted gap keeps its hidden answers on the word: the word's runs carry the
    gap's id as ``kept_gap_id`` (TASK-SKRIPT-40-04-13). The link is not a mark, so
    renderers that read ``marks`` see the word as plain text.

Relationships:
    Imported by ``native_exam_document`` and, for shared instruction bodies, by
    ``native_exam_parent``; this module imports nothing from either, so it stays a leaf.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ASSET_ID_PATTERN,
    GAP_ID_PATTERN,
)

NativeTextMark = Literal["bold", "italic", "underline", "superscript", "subscript"]

NATIVE_TEXT_MARK_ORDER: tuple[NativeTextMark, ...] = (
    "bold",
    "italic",
    "underline",
    "superscript",
    "subscript",
)


def validate_text_only_body(body: tuple[NativeParagraph, ...], *, surface: str) -> None:
    """Choice labels and matching entries carry text paragraphs; interactions cannot nest.

    A QTI simple choice or associable choice holds no nested interaction, and the
    native export has no resource pool for a picture inside one, so a gap or asset
    segment there fails at the model boundary instead of at export time. A kept
    gap link belongs to an item body alone, so a text run carrying one fails here
    too, wherever the body is used outside an item body.
    """
    for paragraph in body:
        for segment in paragraph.segments:
            if not isinstance(segment, NativeTextSegment):
                raise ValueError(f"{surface} body carries text paragraphs only")
            if segment.kept_gap_id is not None:
                raise ValueError(f"{surface} body cannot carry a kept gap link")


class NativeTextSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)
    marks: tuple[NativeTextMark, ...]
    # A reverted gap's hidden answers ride on the word (TASK-SKRIPT-40-04-13 H1):
    # the word's runs carry the kept gap's id, null on ordinary text. The link is
    # not a mark, so ``marks`` keeps its five formatting names. Neighbouring runs
    # merge only when both their marks and their kept links are equal.
    kept_gap_id: str | None = Field(default=None, pattern=GAP_ID_PATTERN)

    @field_validator("marks")
    @classmethod
    def _canonical_marks(cls, marks: tuple[NativeTextMark, ...]) -> tuple[NativeTextMark, ...]:
        if len(set(marks)) != len(marks):
            raise ValueError("text marks must not repeat")
        if "superscript" in marks and "subscript" in marks:
            raise ValueError("superscript and subscript cannot apply to the same text run")
        return tuple(mark for mark in NATIVE_TEXT_MARK_ORDER if mark in marks)


class NativeGapSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["gap"] = "gap"
    gap_id: str = Field(pattern=GAP_ID_PATTERN)


class NativeAssetSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["asset"] = "asset"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)


NativeSegment = Annotated[
    Union[NativeTextSegment, NativeGapSegment, NativeAssetSegment],
    Field(discriminator="kind"),
]


class NativeParagraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # An emptied paragraph has no segments; an empty text run never exists.
    segments: tuple[NativeSegment, ...]
    heading_level: Literal[1, 2, 3] | None


def is_empty_body(body: tuple[NativeParagraph, ...]) -> bool:
    """No gap, no picture and only whitespace text: what the teacher sees as an empty field.

    The same rule as the SPA's ``isEmptyBody`` in ``examWorkspaceRichTextDocument.ts``.
    """
    return all(
        isinstance(segment, NativeTextSegment) and segment.text.strip() == ""
        for paragraph in body
        for segment in paragraph.segments
    )
