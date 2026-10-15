"""Separate item-level points and source answer tails from visible entry content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.source_carrier_context import (
    point_annotation_spans,
    quoted_mask,
)
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
    spans = list(point_annotation_spans(text))
    if facit_text:
        value = facit_text.strip()
        prefix = ANSWER_LABEL.match(value)
        if prefix:
            value = value[prefix.end() :].strip()
        if value:
            mask = quoted_mask(text)
            pattern = re.compile(r"\s*" + r"\s+".join(re.escape(word) for word in value.split()))
            for label in ANSWER_LABEL.finditer(text):
                if mask[label.start()]:
                    continue
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

    The owner's complete quote context decides whether a label is the teacher's
    marker or the entry's own quoted wording, independent of where the model's
    wording anchored or which literal label that wording repeats. Every label
    that starts a line is a marker, so nested aliases leave with their first
    label and later marker lines leave too, while visible continuation lines
    between them stay. When the source's last marker sits mid-line after the
    wording or a continuation, only that marker's line tail leaves. No answer
    value is recovered.
    """
    mask = quoted_mask(text)
    spans: list[tuple[int, int]] = []
    for owner in ownership.owners:
        if owner.start < 0 or owner.end <= owner.start:
            continue
        owned = text[owner.start : owner.end]
        content_start = entry_label_end(owned, owner.ordinal) or 0
        labels = [
            label
            for label in ANSWER_LABEL.finditer(owned, content_start)
            if not mask[owner.start + label.start()]
        ]
        tails: list[tuple[int, int]] = []
        for label in labels:
            line_start = owned.rfind("\n", 0, label.start()) + 1
            if owned[line_start : label.start()].strip():
                continue
            tails.append((label.start(), _tail_line_end(owned, label.end())))
        if labels:
            last = labels[-1]
            if not any(start <= last.start() < end for start, end in tails):
                tails.append((last.start(), _tail_line_end(owned, last.end())))
        for start, end in tails:
            start = _answer_tail_start(content_start, start, owned[content_start:start])
            spans.append((owner.start + start, owner.start + end))
    return tuple(spans)


def _tail_line_end(text: str, label_end: int) -> int:
    """The tail line's end, so later visible continuation lines stay."""
    line_end = text.find("\n", label_end)
    return len(text) if line_end < 0 else line_end


_STRUCTURAL_SEPARATOR = re.compile(r"[\s,;()–—-]*\Z")


def _answer_tail_start(content_start: int, label_start: int, separator: str) -> int:
    """The excluded tail's first character, relative to the owned span.

    The tail starts at the label, or at an opening parenthesis that wraps only
    punctuation around it. A parenthetical wrapper containing prose keeps that
    prose visible.
    """
    opening = separator.rfind("(")
    if opening >= 0 and _STRUCTURAL_SEPARATOR.fullmatch(separator[opening:]):
        return content_start + opening
    return label_start
