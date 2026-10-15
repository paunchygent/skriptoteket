"""The stored retry source of one native exam question (TASK-SKRIPT-39-05-09 D1).

Purpose:
    Hold the records that keep a DOCX question's original conversion source with the
    document, so the question can be reconverted after save and reopen, when the DOCX bytes
    are gone: the pictures a chunk carries by reference, the pictures the source could not
    preserve, one source chunk, and the question's whole source. Nothing here re-runs
    grouping or labeling, and nothing reconstructs source from an edited item.

Relationships:
    Re-exported by ``native_exam_document``, which carries each item's source, and used by
    ``native_exam_retry_source``, which builds and reads the records.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ASSET_ID_PATTERN,
    NativeExamItemKind,
)


class NativeExamRetryImage(BaseModel):
    """One picture a source chunk carries, by reference (TASK-SKRIPT-39-05-09 D1).

    The asset's payload lives once, in the container; this keeps the picture's identity and
    its place in the chunk's plain and marked text so a retry can rebuild the chunk's
    image from the saved document manifest and payload.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    offset: int = Field(ge=0)
    marked_offset: int = Field(ge=0)


class NativeExamRetryMissingImage(BaseModel):
    """A named picture the source could not preserve as a faithful native PNG/JPEG."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reference: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    offset: int = Field(ge=0)
    marked_offset: int = Field(ge=0)


class NativeExamRetryRun(BaseModel):
    """One source run's text and kept marks inside a stored chunk's plain text.

    ``offset`` counts the characters before the run inside the chunk's ``text``, so a
    retry rebuilds the exact source span the deterministic formatting copy reads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int = Field(ge=0)
    text: str
    marks: tuple[str, ...]


class NativeExamRetryParagraph(BaseModel):
    """One source paragraph's text and heading level inside a stored chunk's plain text.

    ``offset`` counts the characters before the paragraph inside the chunk's ``text``,
    and ``heading_level`` is 1-3 for a source heading or a whole paragraph set clearly
    larger than the body text, else None.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int = Field(ge=0)
    text: str
    heading_level: int | None


class NativeExamRetryChunk(BaseModel):
    """One original source chunk kept for a question's retry (TASK-SKRIPT-39-05-09 D1).

    ``text`` is the plain wording people see and ``marked_text`` the model's wording with
    its italics marked, both exactly as the conversion read them. ``runs`` and
    ``paragraphs`` store the chunk's source formatting with offsets into ``text``, so a
    retry copies the marks and heading levels the DOCX reader recorded. ``images`` name
    the pictures the chunk carries, at their places, so a retry rebuilds each image from
    the container's saved payload instead of storing the bytes a second time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    anchor: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    text: str
    marked_text: str
    runs: tuple[NativeExamRetryRun, ...]
    paragraphs: tuple[NativeExamRetryParagraph, ...]
    images: tuple[NativeExamRetryImage, ...] = ()
    missing_images: tuple[NativeExamRetryMissingImage, ...] = ()

    @model_validator(mode="after")
    def _image_offsets_within_text(self) -> "NativeExamRetryChunk":
        """Each picture sits at its exact place in the stored plain and marked text."""
        pictures: tuple[NativeExamRetryImage | NativeExamRetryMissingImage, ...] = (
            *self.images,
            *self.missing_images,
        )
        for image in pictures:
            if image.offset > len(self.text):
                raise ValueError("retry image offset is beyond the chunk's text")
            if image.marked_offset > len(self.marked_text):
                raise ValueError("retry image marked offset is beyond the chunk's marked text")
        return self


class NativeExamRetrySource(BaseModel):
    """The original source and first label of one grouped question (D1).

    The DOCX bytes are gone once conversion ends, so this is the only source a question can
    be reconverted from after save and reopen: ``chunks`` hold the question's own chunks,
    ``key_chunks`` its answer-key chunks, and ``context_chunks`` the read-only shared context
    the conversion read. ``label_kind`` is the labeler's first type, kept before a
    type-conflict resend changed the pipeline's kind.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunks: tuple[NativeExamRetryChunk, ...] = Field(min_length=1)
    key_chunks: tuple[NativeExamRetryChunk, ...] = ()
    context_chunks: tuple[NativeExamRetryChunk, ...] = ()
    label_kind: NativeExamItemKind

    def has_missing_pictures(self) -> bool:
        return any(
            chunk.missing_images for chunk in (*self.chunks, *self.key_chunks, *self.context_chunks)
        )
