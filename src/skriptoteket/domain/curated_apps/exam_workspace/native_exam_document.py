"""Source-neutral native exam document for the teacher exam workspace.

Governing decisions: ADR-SKRIPT-0091, ST-SKRIPT-39-04 (S1-S5), EPIC-SKRIPT-39
terms E8-E12. The document is the versioned Mina filer persistence shape. It
reuses exam IR item semantics (item kinds, answer-key provenance vocabulary)
without mirroring source-format internals: there is exactly one body
representation (paragraph segments with inline gap and asset references),
no source type codes, and no source page/line spans.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
    validate_parent_structure,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION: Literal["native_exam_document_v3"] = "native_exam_document_v3"


class NativeExamAsset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    sha256: str = Field(pattern=SHA256_PATTERN)
    media_type: Literal["image/png", "image/jpeg"]
    byte_length: int = Field(gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class NativeExamDocumentOrigin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["docx_import", "created"]
    source_filename: str | None = None
    source_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    extractor_version: str | None = None

    @model_validator(mode="after")
    def _import_requires_source(self) -> "NativeExamDocumentOrigin":
        if self.kind == "docx_import":
            if not self.source_filename or not self.source_sha256:
                raise ValueError("docx_import origin requires source_filename and source_sha256")
        return self


class NativeExamHeader(BaseModel):
    """Exam header data from the source: never exam text (TASK-SKRIPT-39-05-14 D1).

    ``course_hint`` is the raw text of the source course line; ``printed_total`` is the
    exam total the source prints. Both are metadata, compared or shown, never repeated
    as instructions or item text.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    course_hint: str | None = Field(default=None, min_length=1)
    printed_total: int | float | None = Field(default=None, gt=0)


class NativeExamDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["native_exam_document_v3"] = NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION
    document_id: UUID
    revision: int = Field(ge=1)
    title: str = Field(min_length=1)
    header: NativeExamHeader = NativeExamHeader()
    instructions: tuple[NativeParagraph, ...] = ()
    items: tuple[NativeExamItem, ...] = Field(min_length=1)
    parents: tuple[NativeExamParent, ...] = ()
    assets: tuple[NativeExamAsset, ...] = ()
    origin: NativeExamDocumentOrigin

    @model_validator(mode="after")
    def _document_invariants(self) -> "NativeExamDocument":
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("item ids must be unique")
        sequences = [item.sequence for item in self.items]
        if sequences != list(range(1, len(self.items) + 1)):
            raise ValueError("item sequences must be contiguous from 1 in order")

        asset_ids = [asset.asset_id for asset in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("asset ids must be unique")
        known_assets = set(asset_ids)
        referenced: set[str] = set()
        for item in self.items:
            for asset_id in (*item.body_asset_ids(), *item.source_asset_ids()):
                if asset_id not in known_assets:
                    raise ValueError(f"item {item.item_id} references unknown asset")
                referenced.add(asset_id)
        shared_bodies = (self.instructions, *(parent.instruction for parent in self.parents))
        for body in shared_bodies:
            for paragraph in body:
                for segment in paragraph.segments:
                    if isinstance(segment, NativeGapSegment):
                        raise ValueError("shared instructions cannot contain response gaps")
                    if isinstance(segment, NativeAssetSegment):
                        if segment.asset_id not in known_assets:
                            raise ValueError("shared instructions reference unknown asset")
                        referenced.add(segment.asset_id)
        orphans = known_assets - referenced
        if orphans:
            raise ValueError(f"unreferenced assets: {sorted(orphans)}")
        validate_parent_structure(self.parents, self.items)
        return self

    def parent_of(self, item_id: str) -> NativeExamParent | None:
        return next((parent for parent in self.parents if item_id in parent.item_ids), None)

    def item_by_id(self, item_id: str) -> NativeExamItem:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise DomainError(
            code=ErrorCode.NOT_FOUND,
            message="Exam item not found.",
            details={"item_id": item_id},
        )
