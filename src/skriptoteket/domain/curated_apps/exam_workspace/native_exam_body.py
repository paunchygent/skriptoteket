"""The native exam document body: paragraphs of text, gap and asset segments.

Purpose:
    Hold the one body representation every native exam item uses (ADR-SKRIPT-0091,
    ST-SKRIPT-39-04 S1-S5): paragraphs of text, inline gaps and picture references. The
    document model and the parent/instruction model both read a body, so the segments live
    here instead of either importer. ``native_exam_document`` re-exports every name here.

Relationships:
    Imported by ``native_exam_document`` and, for shared instruction bodies, by
    ``native_exam_parent``; this module imports nothing from either, so it stays a leaf.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ASSET_ID_PATTERN,
    GAP_ID_PATTERN,
)


class NativeTextSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)


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

    segments: tuple[NativeSegment, ...] = Field(min_length=1)
