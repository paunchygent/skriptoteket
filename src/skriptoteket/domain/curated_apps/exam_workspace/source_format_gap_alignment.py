"""Locate a whole ordered gap sequence without guessing repeated inline answers."""

import re

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeGapSegment


def gap_spans(
    text: str, gaps: list[NativeGapSegment], answers: dict[str, tuple[str, ...]]
) -> list[tuple[int, int]] | None:
    """One unique ordered assignment, or None; printed blanks outrank answer words.

    Parentheses immediately wrapping an inline facit answer belong to the gap,
    not to student text. Repeated answers are safe when the entire ordered gap
    sequence has one assignment. Earliest/latest greedy assignments expose any
    ambiguity without enumerating exponentially many possibilities.
    """
    blanks = [(m.start(), m.end()) for m in re.finditer(r"_{2,}|\[\s*\]", text)]
    candidates: list[list[tuple[int, int]]] = []
    for gap in gaps:
        found: set[tuple[int, int]] = set()
        for answer in answers.get(gap.gap_id, ()):
            if not answer.strip():
                continue
            pattern = r"(?<!\w)" + re.escape(answer) + r"(?!\w)"
            for match in re.finditer(pattern, text):
                start, end = match.span()
                if start > 0 and end < len(text) and text[start - 1] == "(" and text[end] == ")":
                    start, end = start - 1, end + 1
                found.add((start, end))
        candidates.append(blanks if len(blanks) == len(gaps) else sorted(found or set(blanks)))
    earliest: list[tuple[int, int]] = []
    cursor = 0
    for options in candidates:
        span = next((span for span in options if span[0] >= cursor), None)
        if span is None:
            return None
        earliest.append(span)
        cursor = span[1]
    latest: list[tuple[int, int]] = []
    cursor = len(text)
    for options in reversed(candidates):
        span = next((span for span in reversed(options) if span[1] <= cursor), None)
        if span is None:
            return None
        latest.append(span)
        cursor = span[0]
    return earliest if earliest == list(reversed(latest)) else None
