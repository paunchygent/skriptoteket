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

from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import NativeExamContentTag
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
    is_empty_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_ordering import (
    ORDERING_IN_PART_POINTS,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
    validate_parent_structure,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
    NativeAnswerKeyRetry,
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION: Literal["native_exam_document_v11"] = (
    "native_exam_document_v11"
)

DocumentImportOriginKind = Literal["docx_import", "pdf_import"]
"""The origin of a document built by the Word import lane, from the uploaded bytes."""


class NativeExamAsset(BaseModel):
    """One picture the document declares; its payload lives in the container.

    ``docx_shapes`` is the self-contained ``w:drawing`` markup of the Word shapes this
    picture was drawn from at import (TASK-SKRIPT-39-04-22 D8, D12). The Word export
    writes those shapes in its place (D9); every other view and export uses the picture.
    A picture the teacher adds is a new asset and carries none (D10).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    sha256: str = Field(pattern=SHA256_PATTERN)
    media_type: Literal["image/png", "image/jpeg"]
    byte_length: int = Field(gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    docx_shapes: str | None = Field(default=None, min_length=1)


class NativeExamDocumentOrigin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["docx_import", "pdf_import", "digiexam_import", "qti_import", "created"]
    source_filename: str | None = None
    source_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    extractor_version: str | None = None

    @model_validator(mode="after")
    def _import_requires_source(self) -> "NativeExamDocumentOrigin":
        if self.kind in {"docx_import", "pdf_import", "digiexam_import", "qti_import"}:
            if not self.source_filename or not self.source_sha256:
                raise ValueError("import origin requires source_filename and source_sha256")
        return self


class ExamCourseChoice(BaseModel):
    """Official course name at the time of the teacher's choice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1)
    name: str = Field(min_length=1)


class NativeExamHeader(BaseModel):
    """Exam header data from the source: never exam text (TASK-SKRIPT-39-05-14 D1).

    ``course_hint`` is the raw text of the source course line; ``printed_total`` is the
    exam total the source prints. Both are metadata, compared or shown, never repeated
    as instructions or item text.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    course: ExamCourseChoice | None = None
    tags: tuple[NativeExamContentTag, ...] = ()
    course_hint: str | None = Field(default=None, min_length=1)
    printed_total: int | float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _clear_previous_course_tags(self) -> "NativeExamHeader":
        """Changing/removing course never carries old-course checklist selections."""
        prefix = f"{self.course.key}:" if self.course is not None else None
        tags = tuple(tag for tag in self.tags if prefix is not None and tag.id.startswith(prefix))
        if tags != self.tags:
            object.__setattr__(self, "tags", tags)
        return self


class NativeExamDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["native_exam_document_v11"] = NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION
    document_id: UUID
    revision: int = Field(ge=1)
    title: str
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
        tag_ids = [tag.id for tag in self.header.tags]
        if len(set(tag_ids)) != len(tag_ids):
            raise ValueError("content tag ids must be unique")
        for tag in self.header.tags:
            if self.header.course is None or not tag.id.startswith(f"{self.header.course.key}:"):
                raise ValueError("content tags must belong to the selected course")
            if not set(tag.question_ids).issubset(item_ids):
                raise ValueError("content tag cites an unknown question")
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
                    if isinstance(segment, NativeTextSegment) and segment.kept_gap_id is not None:
                        raise ValueError("shared instructions cannot carry a kept gap link")
                    if isinstance(segment, NativeAssetSegment):
                        if segment.asset_id not in known_assets:
                            raise ValueError("shared instructions reference unknown asset")
                        referenced.add(segment.asset_id)
        orphans = known_assets - referenced
        if orphans:
            raise ValueError(f"unreferenced assets: {sorted(orphans)}")
        validate_parent_structure(self.parents, self.items)
        child_ids = {item_id for parent in self.parents for item_id in parent.item_ids}
        for item in self.items:
            if item.item_id not in child_ids:
                continue
            if item.kind is not NativeExamItemKind.ORDERING:
                continue
            # An ordering child of a part is always worth 1 point (TASK-SKRIPT-39-06-11 D1).
            if item.points != ORDERING_IN_PART_POINTS:
                raise ValueError("an ordering item inside a parent is worth exactly 1 point")
        return self

    def parent_of(self, item_id: str) -> NativeExamParent | None:
        return next((parent for parent in self.parents if item_id in parent.item_ids), None)

    def printed_instructions(self) -> tuple[NativeParagraph, ...]:
        """The exam instruction the exports print; a whitespace-only one prints nothing."""
        return () if is_empty_body(self.instructions) else self.instructions

    def item_by_id(self, item_id: str) -> NativeExamItem:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise DomainError(
            code=ErrorCode.NOT_FOUND,
            message="Exam item not found.",
            details={"item_id": item_id},
        )


_ANSWER_KEY_RETRY_ORDER: tuple[NativeAnswerKeyRetry, ...] = (
    NativeAnswerKeyRetry.NONE,
    NativeAnswerKeyRetry.OFFERED,
    NativeAnswerKeyRetry.USED,
)


def with_kept_answer_key_retry(
    incoming: NativeExamDocument, saved: NativeExamDocument
) -> NativeExamDocument:
    """Keep the stricter answer-key retry of each saved question (TASK-SKRIPT-40-04-26 D4).

    Every head write applies this, so undo, redo and a save can never move a spent
    retry backwards; questions the saved document does not carry keep their own value.
    """
    saved_by_id = {item.item_id: item for item in saved.items}
    changed = False
    items: list[NativeExamItem] = []
    for item in incoming.items:
        saved_item = saved_by_id.get(item.item_id)
        if saved_item is None or saved_item.answer_key_retry is item.answer_key_retry:
            items.append(item)
            continue
        kept = max(
            item.answer_key_retry,
            saved_item.answer_key_retry,
            key=_ANSWER_KEY_RETRY_ORDER.index,
        )
        if kept is item.answer_key_retry:
            items.append(item)
            continue
        changed = True
        items.append(item.model_copy(update={"answer_key_retry": kept}))
    if not changed:
        return incoming
    return incoming.model_copy(update={"items": tuple(items)})
