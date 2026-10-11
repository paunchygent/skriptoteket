"""Wording as token streams: what the comparator searches, orders and counts.

A token is a casefolded word or a response-gap marker. Punctuation, whitespace, case, quote
style and line breaks never reach a token stream, so they never count in a comparison.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

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


def end_of(haystack: str, phrase: str, start: int = 0) -> int:
    """Where the phrase ends in the stream at or after the start, or -1 when it is absent."""
    needle = f" {phrase} "
    at = haystack.find(needle, start)
    return -1 if at < 0 else at + len(needle) - 1


def occurrences(haystack: str, phrase: str) -> int:
    needle = f" {phrase} "
    count = 0
    at = haystack.find(needle)
    while at >= 0:
        count += 1
        at = haystack.find(needle, at + 1)
    return count


@dataclass(frozen=True)
class Piece:
    """One prompt line or table cell as a phrase, with and without its gap markers."""

    plain: str
    gapped: str

    @property
    def has_gap(self) -> bool:
        return self.gapped != self.plain


def pieces(lines: Iterable[str]) -> tuple[Piece, ...]:
    """Each line and table cell of a gold prompt, without its list label."""
    found: list[Piece] = []
    for line in lines:
        for cell in line.split(CELL_SEPARATOR):
            text = ENTRY_LABEL.sub("", cell)
            if gapped := " ".join(tokens(text)):
                found.append(Piece(" ".join(tokens(text, gaps=False)), gapped))
    return tuple(found)
