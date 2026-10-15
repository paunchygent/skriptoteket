"""Reconstruct an entry's source text when its projection loses marked content.

Each native entry owns its aligned paragraph/line/table-cell envelope. Restoring
that envelope keeps omitted words on the entry, not duplicated in the question.
Only its actual delimited ordinal label has a separate native carrier.
"""

from typing import TypeVar

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeChoice
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    NativeSourceEntry,
    entry_label_end,
    entry_source_extent,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

Entry = TypeVar("Entry", NativeChoice, NativeMatchLeft, NativeMatchRight)


def _entry_extents(source: SourceFormatting) -> list[tuple[int, int]]:
    extents = [
        entry_source_extent(source, NativeSourceEntry("", ordinal, start, end))
        if start >= 0
        else (start, end)
        for ordinal, (start, end) in enumerate(source.entry_spans, 1)
    ]
    # Several options may occupy the same source paragraph/line. Their ordered
    # anchors partition it; an actual next-entry label belongs to that next entry.
    for index in range(1, len(extents)):
        previous_start, previous_end = source.entry_spans[index - 1]
        start, _ = source.entry_spans[index]
        if previous_start < 0 or start < previous_end or extents[index - 1][1] <= extents[index][0]:
            continue
        boundary = previous_end
        for candidate in range(previous_end, start):
            if candidate > previous_end and not source.text[candidate - 1].isspace():
                continue
            if entry_label_end(source.text[candidate:start], index + 1) is not None:
                boundary = candidate
                break
        extents[index - 1] = (extents[index - 1][0], boundary)
        extents[index] = (boundary, extents[index][1])
    return extents


def restore_entries(
    entries: tuple[Entry, ...], source: SourceFormatting, covered: set[int]
) -> tuple[Entry, ...]:
    """Recover omitted marked words on their source-backed native entry surface."""
    result: list[Entry] = []
    for ordinal, (entry, (start, end)) in enumerate(
        zip(entries, _entry_extents(source), strict=True), 1
    ):
        if start < 0:
            result.append(entry)
            continue
        left, right = start, end
        anchor_start = source.entry_spans[ordinal - 1][0]
        # A prompt or another surface can share this physical paragraph. Its
        # represented prefix stays on that surface, not on the rebuilt entry.
        for index in range(left, anchor_start):
            if index in covered:
                left = index + 1
        label_end = entry_label_end(source.text[left:right], ordinal)
        content_start = left + (label_end or 0)
        source.covered.update(range(left, content_start))
        covered.update(range(left, content_start))
        missing = any(
            source.marks[index] and not source.text[index].isspace() and index not in covered
            for index in range(content_start, right)
        )
        if missing:
            body = tuple(source.fragments(content_start, right))
            entry = entry.model_copy(update={"body": body})
            source.path = "rebuilt"
            source.covered.update(range(left, right))
            covered.update(range(left, right))
        result.append(entry)
    return tuple(result)
