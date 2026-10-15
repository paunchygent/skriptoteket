"""Coordinate-preserving source partitions for native editing surfaces."""

import re
from collections.abc import Iterable, Iterator


def normalized_source_index(text: str) -> tuple[str, list[int]]:
    """Fold whitespace while retaining each normalized character's source offset."""
    chars: list[str] = []
    positions: list[int] = []
    for offset, char in enumerate(text):
        if char.isspace():
            if chars and chars[-1] != " ":
                chars.append(" ")
                positions.append(offset)
        else:
            chars.append(char)
            positions.append(offset)
    if chars and chars[-1] == " ":
        chars.pop()
        positions.pop()
    return "".join(chars), positions


def visible_intervals(
    start: int, end: int, excluded: Iterable[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Subtract owned entry intervals without changing any source coordinate."""
    result: list[tuple[int, int]] = []
    cursor = start
    for left, right in sorted(excluded):
        if right <= cursor or left >= end:
            continue
        if left > cursor:
            result.append((cursor, min(left, end)))
        cursor = max(cursor, right)
    if cursor < end:
        result.append((cursor, end))
    return result


def overlaps(start: int, end: int, excluded: Iterable[tuple[int, int]]) -> bool:
    return any(left < end and right > start for left, right in excluded)


def paragraph_intervals(
    paragraphs: Iterable[tuple[int, int, int | None]],
    excluded: tuple[tuple[int, int], ...],
    text_length: int,
) -> list[tuple[int, int, int | None]]:
    """Intersect ordered paragraphs with the partition in one forward sweep."""
    visible = visible_intervals(0, text_length, excluded)
    result: list[tuple[int, int, int | None]] = []
    cursor = 0
    for start, end, heading in paragraphs:
        while cursor < len(visible) and visible[cursor][1] <= start:
            cursor += 1
        index = cursor
        while index < len(visible) and visible[index][0] < end:
            left, right = visible[index]
            result.append((max(start, left), min(end, right), heading))
            if right >= end:
                break
            index += 1
        cursor = index
    return result


def entry_unit_intervals(
    text: str, paragraphs: Iterable[tuple[int, int, int | None]]
) -> Iterator[tuple[int, int, int | None]]:
    """Index existing paragraph/line/table-cell boundaries in one source sweep."""
    for left, right, heading in paragraphs:
        start = left
        for separator in re.finditer(r"\n| \| ", text[left:right]):
            end = left + separator.start()
            if start < end:
                yield start, end, heading
            start = left + separator.end()
        if start < right:
            yield start, right, heading


def question_label_span(
    text: str, paragraphs: Iterable[tuple[int, int]], labels: tuple[str, ...]
) -> tuple[int, int] | None:
    """Locate one complete printed identifier, never a prefix of content.

    Question labels may contain words (``Question 4``), letters or numbers.
    The located token owns its immediate delimiter and following whitespace,
    not punctuation that starts the question wording after that separator.
    """
    for start, finish in paragraphs:
        prefix = text[start:finish]
        leading = len(prefix) - len(prefix.lstrip())
        label = next(
            (label for label in labels if label and prefix.startswith(label, leading)), None
        )
        if label is None:
            continue
        end = leading + len(label)
        if end < len(prefix) and (
            not (prefix[end].isspace() or prefix[end] in ".):-")
            or (prefix[end] in ".," and prefix[end + 1 : end + 2].isdigit())
        ):
            continue
        if end < len(prefix) and prefix[end] in ".):-":
            end += 1
        while end < len(prefix) and prefix[end].isspace():
            end += 1
        return start, start + end
    return None
