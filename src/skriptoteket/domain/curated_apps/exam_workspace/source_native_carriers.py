"""Separate item-level points and source answer tails from visible entry content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import ANSWER_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import entry_label_end

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.source_entry_ownership import (
        EntryOwnership,
        EntrySurface,
    )


def native_carrier_spans(text: str, facit_text: str | None) -> tuple[tuple[int, int], ...]:
    """Locate printed points and the actual native facit's verbatim source span.

    An identical answer word inside an option is not the teacher's facit span:
    its existing answer label must identify it too.
    """
    spans = [(match.start(), match.end()) for match in POINT_LABEL.finditer(text)]
    if facit_text:
        value = facit_text.strip()
        prefix = ANSWER_LABEL.match(value)
        if prefix:
            value = value[prefix.end() :].strip()
        if value:
            pattern = re.compile(r"\s*" + r"\s+".join(re.escape(word) for word in value.split()))
            for label in ANSWER_LABEL.finditer(text):
                matched = pattern.match(text, label.end())
                if matched is None:
                    continue
                if value[-1].isalnum() and text[matched.end() : matched.end() + 1].isalnum():
                    continue
                spans.append((label.start(), matched.end()))
    return tuple(sorted(spans))


def entry_answer_spans(
    text: str, ownership: EntryOwnership, surfaces: tuple[EntrySurface, ...]
) -> tuple[tuple[int, int], ...]:
    """Identify answer tails beyond an entry's aligned wording, without deriving a key.

    Reuse the existing inline-answer recogniser on the complete source owner,
    not just the separator immediately after model-aligned text. Continuation
    words and their punctuation do not change label recognition. Quoted literal
    labels and labels supplied as part of the model entry remain visible, as
    in the existing character-alignment rule. No answer value is recovered.
    """
    texts = {surface.sequence: surface.texts for surface in surfaces}
    spans: list[tuple[int, int]] = []
    for owner in ownership.owners:
        if owner.start < 0:
            continue
        wording = texts[owner.sequence][owner.ordinal - 1]
        if ANSWER_LABEL.search(wording):
            continue
        # Structural ownership survives a rewrite even when no wording anchor
        # does. Recognition is source-owned, not contingent on model equality.
        content_start = owner.start + (
            entry_label_end(text[owner.start : owner.end], owner.ordinal) or 0
        )
        anchor_end = max(content_start, owner.anchor_end)
        for label in ANSWER_LABEL.finditer(text, anchor_end, owner.end):
            separator = text[anchor_end : label.start()]
            start = _answer_tail_start(anchor_end, label.start(), separator)
            if start is None:
                continue
            line_end = text.find("\n", label.end(), owner.end)
            spans.append((start, line_end if line_end >= 0 else owner.end))
            break
    return tuple(spans)


_STRUCTURAL_SEPARATOR = re.compile(r"[\s,;()–—-]*\Z")


def _answer_tail_start(anchor_end: int, label_start: int, separator: str) -> int | None:
    """The excluded tail's first character, or None when the label is prose.

    The tail starts at the label, or at an opening parenthesis that wraps only
    punctuation around it. A parenthetical wrapper containing prose keeps that
    prose visible. Quote context distinguishes a literal label from the shared
    recogniser's answer marker; a continuation needs no particular punctuation.
    """
    opening = separator.rfind("(")
    if opening >= 0 and _STRUCTURAL_SEPARATOR.fullmatch(separator[opening:]):
        return anchor_end + opening
    quote: str | None = None
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’", "`": "`"}
    for index, char in enumerate(separator):
        if quote is not None:
            if char == quote:
                quote = None
        elif char in pairs and not (char == "'" and index and separator[index - 1].isalnum()):
            quote = pairs[char]
    return None if quote is not None else label_start
