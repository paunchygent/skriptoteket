"""Project each native entry's produced wording inside its owned source span.

The ownership partition assigns every entry character to exactly one surface, so
a surface's projection, rebuild and coverage only ever touch its own span: no
left entry can copy a right entry's words, and marking one entry represented
cannot satisfy another entry's formatting. An owned continuation paragraph that
carries a heading level is emitted on the entry itself when the model omitted
it, so the question body's heading merge never has to claim it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeChoice
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_ownership import (
    EntryOwner,
    EntryOwnership,
    EntrySurface,
    produced_entry_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    align_paragraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    entry_label_end,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
    SourceParagraph,
)

Entry = TypeVar("Entry", NativeChoice, NativeMatchLeft, NativeMatchRight)


@dataclass
class _OwnedSpan:
    """One entry's accounted source span, carried from projection into repair."""

    start: int
    end: int
    content_start: int
    emitted: bool


def apply_entry_ownership(
    ownership: EntryOwnership,
    surface: EntrySurface,
    entries: tuple[Entry, ...],
    *,
    body_source: SourceFormatting,
) -> tuple[Entry, ...]:
    """Project one surface's entries inside the owners the shared partition assigned.

    A surface accounts only its own span on top of the question body's coverage:
    the body may own a prompt prefix inside a shared paragraph, but it can never
    satisfy an entry's marked content, and one entry can never satisfy another.
    """
    owners = ownership.for_surface(surface.sequence)
    if len(owners) != len(entries) or len(owners) != len(surface.texts):
        raise ValueError("entry ownership does not match the produced entries")
    source = surface.source
    body_covered = frozenset(body_source.covered)
    result: list[Entry] = []
    spans: list[_OwnedSpan | None] = []
    for entry, text, owner in zip(entries, surface.texts, owners, strict=True):
        projected, span = _project_entry(text, entry, owner, source, body_covered)
        result.append(projected)
        spans.append(span)
    covered = set(body_source.covered) | set(source.covered)
    projected_paragraphs = set(body_source.projected) | set(source.projected)
    for index, (entry, span) in enumerate(zip(result, spans, strict=True)):
        if span is None or span.emitted:
            continue
        if not _needs_rebuild(ownership, source, span, covered, projected_paragraphs):
            continue
        result[index] = _rebuild_entry(entry, source, span)
        projected_paragraphs.update(source.projected)
    return tuple(result)


def _project_entry(
    text: str,
    entry: Entry,
    owner: EntryOwner,
    source: SourceFormatting,
    body_covered: frozenset[int],
) -> tuple[Entry, _OwnedSpan | None]:
    if owner.start < 0:
        source.entry_spans.append((-1, -1))
        return entry, None
    start = owner.start
    if owner.first_in_unit:
        start = _extend_left(start, owner.unit_start, body_covered)
    stop = owner.anchor_start if owner.anchor_start >= 0 else start
    start = _skip_covered(source, start, stop, body_covered)
    content_start = _content_start(source, owner, start)
    source.covered.update(range(start, content_start))
    span = _OwnedSpan(start=start, end=owner.end, content_start=content_start, emitted=False)
    if (
        owner.exact
        and owner.anchor_start >= 0
        and start <= owner.anchor_start
        and owner.anchor_end <= owner.end
    ):
        source.covered.update(range(owner.anchor_start, owner.anchor_end))
        source.entry_spans.append((owner.anchor_start, owner.anchor_end))
        body = tuple(source.fragments(owner.anchor_start, owner.anchor_end))
        return entry.model_copy(update={"body": body}), span
    paragraph = _single_paragraph(source, start, owner.end)
    if paragraph is not None:
        aligned, lost, represented = align_paragraph(
            produced_entry_body(text)[0],
            source.text[start : owner.end],
            source.marks[start : owner.end],
            paragraph.heading,
            {},
            source.ignored,
        )
        if not lost:
            source.covered.update(start + index for index in represented)
            source.projected.add(paragraph.start)
            source.entry_spans.append(
                (start + min(represented), start + max(represented) + 1)
                if represented
                else (-1, -1)
            )
            if source.path == "exact":
                source.path = "aligned"
            return entry.model_copy(update={"body": (aligned,)}), span
    source.entry_spans.append((owner.anchor_start, owner.anchor_end))
    return _rebuild_entry(entry, source, span), span


def _extend_left(start: int, lower: int, blocked: frozenset[int]) -> int:
    """Claim an unlabelled unit prefix, stopping at the question body's own text."""
    while start > lower and (start - 1) not in blocked:
        start -= 1
    return start


def _skip_covered(source: SourceFormatting, start: int, stop: int, covered: frozenset[int]) -> int:
    trimmed = start
    for index in range(start, stop):
        if index in covered:
            trimmed = index + 1
    return trimmed


def _content_start(source: SourceFormatting, owner: EntryOwner, start: int) -> int:
    """Skip this entry's own label: the native field already carries its ordinal."""
    if owner.label_start is not None:
        length = entry_label_end(source.text[owner.label_start : owner.end], owner.ordinal) or 0
        return max(owner.label_start + length, start)
    length = entry_label_end(source.text[start : owner.end], owner.ordinal) or 0
    return start + length


def _single_paragraph(source: SourceFormatting, start: int, end: int) -> SourceParagraph | None:
    paragraphs = [
        paragraph
        for paragraph in source.paragraphs
        if paragraph.start < end and paragraph.end > start
    ]
    return paragraphs[0] if len(paragraphs) == 1 else None


def _needs_rebuild(
    ownership: EntryOwnership,
    source: SourceFormatting,
    span: _OwnedSpan,
    covered: set[int],
    projected_paragraphs: set[int],
) -> bool:
    """A marked character or an omitted owned heading must be emitted by this entry."""
    for index in range(span.content_start, span.end):
        if source.marks[index] and not source.text[index].isspace() and index not in covered:
            return True
    for paragraph in source.paragraphs:
        if paragraph.start >= span.end or paragraph.end <= span.start:
            continue
        if paragraph.heading is None or paragraph.start in ownership.heading_chunk_paragraphs:
            continue
        if paragraph.start not in projected_paragraphs:
            return True
    return False


def _rebuild_entry(entry: Entry, source: SourceFormatting, span: _OwnedSpan) -> Entry:
    """Recover the owned span's source wording with its marks and heading levels."""
    end = span.end
    while end > span.content_start and source.text[end - 1].isspace():
        end -= 1
    body = tuple(source.fragments(span.content_start, end))
    span.emitted = True
    if not body:
        return entry
    source.covered.update(range(span.start, span.end))
    source.path = "rebuilt"
    return entry.model_copy(update={"body": body})
