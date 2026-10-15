"""Separate item-level points and source answer tails from visible entry content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import ANSWER_LABEL

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

    Reuse the existing inline-answer recogniser. The source label must follow
    the entry's wording with only a structural separator between them. A label
    inside the entry's aligned wording, or inside an ordinary continuation
    sentence, remains entry content. A literal label supplied as part of the
    entry is also retained, as in the existing character-alignment rule.
    """
    texts = {surface.sequence: surface.texts for surface in surfaces}
    spans: list[tuple[int, int]] = []
    for owner in ownership.owners:
        if owner.anchor_end < 0:
            continue
        wording = texts[owner.sequence][owner.ordinal - 1]
        if ANSWER_LABEL.search(wording):
            continue
        label = ANSWER_LABEL.search(text, owner.anchor_end, owner.end)
        if label is None:
            continue
        separator = text[owner.anchor_end : label.start()]
        if re.fullmatch(r"[\s,;()–—-]*", separator) is None:
            continue
        start = label.start()
        opening = separator.rfind("(")
        if opening >= 0:
            start = owner.anchor_end + opening
        line_end = text.find("\n", label.end(), owner.end)
        spans.append((start, line_end if line_end >= 0 else owner.end))
    return tuple(spans)
