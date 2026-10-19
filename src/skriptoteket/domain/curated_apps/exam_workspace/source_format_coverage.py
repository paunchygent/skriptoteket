"""Admit an item's typography only after accounting for every visible source mark.

A native entry's own label is exempt only when the entry's aligned source span
and that entry's rendered ordinal identity together reconstruct it exactly:
first choice A/a/1/i, second B/b/2/ii, and so on. No arbitrary word before an
entry body ever becomes an exemption.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
)

_LABEL_SEPARATORS = ".:;-–—"

_ORDINAL_FAMILIES = ("upper", "lower", "decimal", "roman_upper", "roman_lower")
_ROMAN_NUMERALS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


@dataclass(frozen=True)
class NativeSourceEntry:
    """One native choice or matching entry's aligned source span, for label accounting.

    ``sequence`` names the rendered surface (choices, match_left, match_right) and
    ``ordinal`` is the entry's 1-based rendered position: the first choice is A/a/1/i,
    the second B/b/2/ii. ``start`` and ``end`` are the entry body wording's character
    span in the item's source chunks; ``start`` alone anchors its printed label.
    """

    sequence: str
    ordinal: int
    start: int
    end: int


def _letters(ordinal: int, *, upper: bool) -> str:
    """Spreadsheet-style alphabetic ordinal: A..Z, AA..ZZ, AAA, without a cap."""
    chars: list[str] = []
    value = ordinal
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        chars.append(chr(ord("A") + remainder))
    token = "".join(reversed(chars))
    return token if upper else token.lower()


def _ordinal_token(family: str, ordinal: int) -> str | None:
    if ordinal < 1:
        return None
    if family == "upper":
        return _letters(ordinal, upper=True)
    if family == "lower":
        return _letters(ordinal, upper=False)
    if family == "decimal":
        return str(ordinal)
    value, token = ordinal, []
    for amount, letter in _ROMAN_NUMERALS:
        while value >= amount:
            token.append(letter)
            value -= amount
    return "".join(token).lower() if family == "roman_lower" else "".join(token)


def entry_label_end(text: str, ordinal: int) -> int | None:
    """End of this native ordinal's delimited prefix, never a prefix inside a word.

    Delimiters distinguish an identifier from content (A. / a) / [1]), while
    the native entry's ordinal determines the identifier itself. Remaining
    words are content, even when the model omitted them.
    """
    at = 0
    while at < len(text) and text[at].isspace():
        at += 1
    opened = text[at] if at < len(text) and text[at] in "([{" else ""
    if opened:
        at += 1
    for family in _ORDINAL_FAMILIES:
        token = _ordinal_token(family, ordinal)
        if token is None or not text.startswith(token, at):
            continue
        end = at + len(token)
        if opened:
            closing = {"(": ")", "[": "]", "{": "}"}[opened]
            if end >= len(text) or text[end] != closing:
                continue
            end += 1
        elif end < len(text) and text[end] in ")]}" + _LABEL_SEPARATORS:
            end += 1
        else:
            continue
        while end < len(text) and text[end] in _LABEL_SEPARATORS:
            end += 1
        while end < len(text) and text[end].isspace():
            end += 1
        return end
    return None


def _is_ordinal_label(prefix: str, ordinal: int) -> bool:
    return entry_label_end(prefix, ordinal) == len(prefix)


def entry_source_extent(source: SourceFormatting, entry: NativeSourceEntry) -> tuple[int, int]:
    """An aligned entry's source paragraph, physical line or table cell envelope."""
    first = source.entry_unit_at(entry.start)
    last = source.entry_unit_at(entry.end - 1)
    if first is None or last is None:
        return entry.start, entry.end
    return first.start, last.end


def _entry_label_characters(
    source: SourceFormatting, entries: Iterable[NativeSourceEntry]
) -> set[int]:
    """The characters the item's native entry structure already carries.

    An entry's aligned body span fixes where its own label ends; the prefix is
    exempt only when it is exactly that entry's rendered ordinal identity.
    """
    covered: set[int] = set()
    for entry in entries:
        if entry.start < 0 or entry.end <= entry.start:
            continue
        unit = source.entry_unit_at(entry.start)
        if unit is None:
            continue
        boundary = unit.start
        if boundary >= entry.start:
            continue
        if _is_ordinal_label(source.text[boundary : entry.start], entry.ordinal):
            covered.update(range(boundary, entry.start))
    return covered


def complete_source_formatting(
    chunks: tuple[DocxChunk, ...],
    sources: Iterable[SourceFormatting],
    body_source: SourceFormatting,
    body: tuple[NativeParagraph, ...],
    *,
    printed_label: str | None,
    answers: dict[str, tuple[str, ...]],
    can_rebuild_body: bool,
    entries: Iterable[NativeSourceEntry] = (),
) -> tuple[NativeParagraph, ...]:
    source_list = tuple(sources)
    covered = set().union(*(source.covered for source in source_list))
    covered.update(_entry_label_characters(body_source, entries))
    projected = set(body_source.projected)
    for source in source_list:
        projected.update(source.projected)
    heading_chunk_paragraphs: set[int] = set()
    offset = 0
    for index, chunk in enumerate(chunks):
        if index:
            offset += 1
        # Assembly deterministically places source heading chunks; they are not
        # required to appear in the model's body before that placement happens.
        if chunk.kind == "heading":
            covered.update(range(offset, offset + len(chunk.text)))
            heading_chunk_paragraphs.update(
                offset + paragraph.offset for paragraph in chunk.paragraphs
            )
        offset += len(chunk.text)
    if body_source.label_span is not None:
        covered.update(range(*body_source.label_span))
    missing = [
        index
        for index, marks in enumerate(body_source.marks)
        if marks and not body_source.text[index].isspace() and index not in covered
    ]
    # A heading level is deterministic source formatting too, equally for a
    # size-derived or table-contained heading paragraph with no run marks.
    unprojected_headings = [
        paragraph
        for paragraph in body_source.paragraphs
        if paragraph.heading is not None
        and paragraph.start not in heading_chunk_paragraphs
        and paragraph.start not in projected
    ]
    if unprojected_headings:
        # Restore only the omitted source-backed blocks. Existing native
        # paragraphs retain their atoms (pictures/gaps), wording and ownership;
        # choices and matching entries never enter the question body.
        merged = list(zip(body_source.output_anchors, body, strict=True))
        for paragraph in unprojected_headings:
            start = paragraph.start
            if body_source.label_span is not None and start == body_source.label_span[0]:
                start = body_source.label_span[1]
            restored = body_source.fragments(start, paragraph.end)
            insertion = next(
                (index for index, (anchor, _) in enumerate(merged) if anchor > paragraph.start),
                len(merged),
            )
            merged[insertion:insertion] = [(paragraph.start, value) for value in restored]
            covered.update(range(paragraph.start, paragraph.end))
            body_source.covered.update(range(paragraph.start, paragraph.end))
        body_source.path = "rebuilt"
        body = tuple(value for _, value in merged)
        body_source.output_anchors = [anchor for anchor, _ in merged]
        missing = [index for index in missing if index not in covered]
    if not missing:
        return body
    if not can_rebuild_body:
        raise FormattingTransferError("unrepresented source marks cannot be isolated from entries")
    return body_source.rebuild_body(answers)
