"""The source paragraphs of one question, and which a reworded reply paragraph overlaps most.

When a reply paragraph no longer prints its source span, source formatting may still align
or rebuild it from one source paragraph: the one sharing the most word tokens with it,
case folded. Scoring only ranks candidates; the caller decides what a tie or a zero means.
"""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceParagraph:
    start: int
    end: int
    heading: int | None


def _words(text: str) -> Counter[str]:
    return Counter(re.findall(r"\w+", text.casefold()))


def overlap_scores(
    text: str, source_text: str, candidates: Sequence[SourceParagraph]
) -> list[tuple[int, SourceParagraph]]:
    """Each candidate with the number of word tokens it shares with ``text``."""
    words = _words(text)
    return [(sum((words & _words(source_text[p.start : p.end])).values()), p) for p in candidates]
