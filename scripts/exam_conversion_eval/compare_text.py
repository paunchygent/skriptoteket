"""Wording as token streams: what the comparator searches and counts.

A token is a casefolded word or a response-gap marker. Punctuation, whitespace, case, quote
style and line breaks never reach a token stream, so they never count in a comparison.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

GAP_MARKER = "[___]"
CELL_SEPARATOR = " | "
# A list label opening a prompt line or table cell: a letter or a number with its closing mark.
ENTRY_LABEL = re.compile(r"^\s*(?:[A-Za-z]|\d{1,3})\s*[.)]\s+")
_TOKEN = re.compile(r"\[___\]|\w+")


def tokens(text: str, *, gaps: bool = True) -> tuple[str, ...]:
    found = _TOKEN.findall(text.casefold())
    return tuple(token for token in found if gaps or token != GAP_MARKER)


def words(text: str) -> str:
    """Wording alone, without gap markers."""
    return " ".join(tokens(text, gaps=False))


def stream(texts: Iterable[str], *, gaps: bool = False) -> str:
    """Several texts as one space-padded token string, so a phrase is a substring search."""
    joined = " ".join(token for text in texts for token in tokens(text, gaps=gaps))
    return f" {joined} "


def occurrences(haystack: str, phrase: str) -> int:
    needle = f" {phrase} "
    count = 0
    at = haystack.find(needle)
    while at >= 0:
        count += 1
        at = haystack.find(needle, at + 1)
    return count


def word_set(texts: Iterable[str]) -> frozenset[str]:
    """Every word across the texts; gap markers are not words."""
    return frozenset(token for text in texts for token in tokens(text, gaps=False))


def without_list_labels(lines: Iterable[str]) -> tuple[str, ...]:
    """Each line and table cell of a gold prompt without its list label."""
    return tuple(ENTRY_LABEL.sub("", cell) for line in lines for cell in line.split(CELL_SEPARATOR))
