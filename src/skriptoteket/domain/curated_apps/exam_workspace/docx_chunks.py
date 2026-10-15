"""Ordered source text and embedded pictures for the exam workspace DOCX conversion lane."""

import hashlib
from dataclasses import dataclass
from typing import Literal


def asset_id_for(payload: bytes) -> str:
    """Content-addressed id of one embedded picture: ``asset_`` plus 16 hex digits."""
    return f"asset_{hashlib.sha256(payload).hexdigest()[:16]}"


@dataclass(frozen=True)
class DocxImage:
    """One PNG or JPEG picture embedded in a body block, at its place in the block.

    ``offset`` is the picture's position in the block's plain text and ``marked_offset``
    its position in ``marked_text``; both count the characters before the picture, so a
    picture mid-paragraph splits the text instead of moving to the end.
    """

    payload: bytes
    media_type: Literal["image/png", "image/jpeg"]
    offset: int = 0
    marked_offset: int = 0
    width: int | None = None
    height: int | None = None

    @property
    def asset_id(self) -> str:
        """The deterministic id the native document and its container reference."""
        return asset_id_for(self.payload)


@dataclass(frozen=True)
class DocxMissingImage:
    """One embedded picture the chunker could not turn into a ``DocxImage``.

    ``reference`` names the source part (its partname, or the relationship id when the
    relationship has no part) and ``media_type`` its declared media type. ``offset`` and
    ``marked_offset`` are the picture's place in the chunk's plain and marked text, exactly
    like ``DocxImage``. A missing picture never disappears silently: the native build turns
    it into a named teacher-review reason.
    """

    reference: str
    media_type: str
    offset: int = 0
    marked_offset: int = 0


@dataclass(frozen=True)
class DocxSourceRun:
    """One source run's text and kept marks, at its place in the chunk's plain ``text``.

    ``offset`` counts the characters before the run inside its chunk's ``text``, so a
    run is the exact source span the deterministic copy applies its marks to. ``marks``
    is a subset of ``bold``, ``italic``, ``underline``, ``superscript`` and
    ``subscript`` in that fixed order, resolved from the run's direct font formatting,
    its character-style and paragraph-style chains and the document defaults. A run
    without text contributes no span and is not listed.
    """

    offset: int
    text: str
    marks: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocxSourceParagraph:
    """One source paragraph or table cell paragraph, at its place in the chunk's ``text``.

    ``offset`` counts the characters before the paragraph inside its chunk's ``text``
    and ``text`` is the paragraph's own text, so the paragraphs of a chunk cover it in
    order with the table cell and row separators between them. ``heading_level`` is 1-3
    for a Title, a Heading 1-3 or a whole paragraph clearly larger than the body text,
    else None.
    """

    offset: int
    text: str
    heading_level: int | None = None


@dataclass(frozen=True)
class DocxChunk:
    """Plain source text for people; marked_text wraps italic runs in <i>...</i> for the model.

    ``runs`` and ``paragraphs`` are the chunk's source formatting: every source run's
    kept marks and every source paragraph's heading level, both with offsets into this
    chunk's plain ``text``. ``marked_text`` and the picture offsets stay exactly as the
    model and the native build already read them.
    """

    anchor: str
    kind: str
    text: str
    marked_text: str
    images: tuple[DocxImage, ...] = ()
    missing_images: tuple[DocxMissingImage, ...] = ()
    runs: tuple[DocxSourceRun, ...] = ()
    paragraphs: tuple[DocxSourceParagraph, ...] = ()
