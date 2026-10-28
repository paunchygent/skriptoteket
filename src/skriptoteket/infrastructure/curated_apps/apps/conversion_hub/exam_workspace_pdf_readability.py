"""Judge one text PDF page's text layer by its mapped and unmapped glyphs (ST-SKRIPT-39-10 P2, P7).

A PDF saved from Word or Google Docs maps its characters through each font's ToUnicode
table, so the page reader finds real words. A PDF whose text layer is broken instead
gives pdfminer's ``(cid:NN)`` placeholders, replacement characters or private-use
characters: the reader knows a glyph sits on the page but not which character it is. A
page with a few such glyphs still reads; a page that is mostly unmapped glyphs cannot be
read as text, so the import skips it and names it, and a PDF with no readable page stops
with the import's message.

The measure is deterministic and character based over the words the page reader already
extracted, so judging a page adds no parsing pass. A page with no non-whitespace glyph at
all is no text: pictures alone are no readable content.

Relationships:
    ``exam_workspace_pdf_layout`` judges every page's words with ``page_text_state`` and
    skips the pages whose text layer cannot be read;
    ``exam_workspace_pdf_chunker`` stops a PDF that has no readable page or no text block;
    ``exam_workspace_pdf_items`` holds ``PdfWord``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfWord,
)

# pdfminer's placeholder for a glyph its font did not map to a character.
_CID = re.compile(r"\(cid:\d+\)")
# A page stays readable while at most this share of its glyphs is unmapped: more than
# half unreadable glyphs means the text layer, not a few symbols, is broken.
_MAX_UNMAPPED_SHARE = 0.5

PageTextState = Literal["readable", "garbled", "empty"]


def page_text_state(words: Sequence[PdfWord]) -> PageTextState:
    """Whether the page's words read as text, are mostly unmapped glyphs, or hold none.

    ``garbled`` covers both a page of placeholders and a page whose glyphs are mostly
    unmapped; ``empty`` is a page with no non-whitespace glyph at all.
    """
    mapped, unmapped = _glyph_counts("".join(word.text for word in words))
    if mapped + unmapped == 0:
        return "empty"
    if mapped > 0 and unmapped / (mapped + unmapped) <= _MAX_UNMAPPED_SHARE:
        return "readable"
    return "garbled"


def page_readable(words: Sequence[PdfWord]) -> bool:
    """The page's words read as text: some mapped glyphs, and at most half unmapped."""
    return page_text_state(words) == "readable"


def _glyph_counts(text: str) -> tuple[int, int]:
    """The text's mapped glyphs and its unmapped glyphs, as ``(mapped, unmapped)``."""
    placeholders = len(_CID.findall(text))
    remaining = _CID.sub("", text)
    unmapped = placeholders + sum(1 for character in remaining if _unmapped(character))
    mapped = sum(
        1 for character in remaining if not character.isspace() and not _unmapped(character)
    )
    return mapped, unmapped


def _unmapped(character: str) -> bool:
    """A replacement character or a private-use character: a glyph with no known character."""
    code = ord(character)
    return (
        character == "\ufffd"
        or 0xE000 <= code <= 0xF8FF
        or 0xF0000 <= code <= 0xFFFFD
        or 0x100000 <= code <= 0x10FFFD
    )
