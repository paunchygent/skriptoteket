"""Shared source-text context: quoted phrases and printed point annotations.

Quotation decides whether a point-like or answer-like label is the teacher's
metadata or the student's visible wording, in one place so entry projection,
body reconstruction and coverage agree. Straight quotes, English smart quotes
and the Swedish right double quote are supported; the Swedish ``”citat”``
form opens and closes with the same character. A printed point label is an
annotation only when its line detaches it from the sentence: the whole line is
a points line, or the label leads or ends the line with no word beside it. A
label beside an operator, between words, one whose sentence continues past it,
or one inside a quoted phrase is the source's student-visible content, while a
label after a completed sentence is detached metadata.
"""

from __future__ import annotations

import re

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    points_line,
)

_QUOTE_PAIRS = {
    '"': '"',
    "'": "'",
    "“": "”",
    "”": "”",
    "‘": "’",
    "`": "`",
}
_APOSTROPHES = ("'",)
_WORD = re.compile(r"\w")
_SENTENCE_END = re.compile(r"[.!?…]\W*\Z")
_IMPLICIT_FACTOR = re.compile(r"\A\s*[A-Za-z0-9][.!?]?\s*\Z")
_MATH_SYMBOLS = "×⋅∙*+/=<>≤≥≠≈^±−-"
_MATH_WORDS = ("times", "plus", "minus", "gånger", "ganger", "divided")
_MATH_OPERATOR_SUFFIX = re.compile(
    r"(?:[" + re.escape(_MATH_SYMBOLS) + r"]|\b(?:" + "|".join(_MATH_WORDS) + r"))\s*\Z",
    re.IGNORECASE,
)
_MATH_OPERATOR_PREFIX = re.compile(
    r"\A\s*(?:[" + re.escape(_MATH_SYMBOLS) + r"]|\b(?:" + "|".join(_MATH_WORDS) + r")\b)",
    re.IGNORECASE,
)


def quoted_mask(text: str) -> tuple[bool, ...]:
    """Whether each character lies inside a completed quoted phrase.

    An open phrase closes at its matching quote even after a letter, so a
    single-quoted phrase round-trips while an apostrophe inside a word opens
    nothing. The Swedish right double quote opens a phrase as well as closing
    one, so ``”citat”`` is recognised without special-casing its wording. An
    unmatched delimiter, such as the inch mark in ``5"``, masks nothing: it
    must never shield a genuine source answer tail that follows it.
    """
    mask = [False] * len(text)
    closing: str | None = None
    opening = 0
    for index, char in enumerate(text):
        if closing is not None:
            if char == closing:
                for inside in range(opening, index + 1):
                    mask[inside] = True
                closing = None
        elif char in _QUOTE_PAIRS and not (
            char in _APOSTROPHES and index and text[index - 1].isalnum()
        ):
            closing = _QUOTE_PAIRS[char]
            opening = index
    return tuple(mask)


def point_annotation_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Locate printed score annotations, never point-like visible content.

    The line's own structure decides. The label is an annotation when its
    line is a points line or when the label leads or ends the line with no word
    beside it, including after a completed sentence. An operator directly
    beside the parenthesis, a single implicit multiplication factor after it,
    a label between words, and a quoted label are math grammar or sentence
    evidence that the label is student-visible content.
    """
    mask = quoted_mask(text)
    spans: list[tuple[int, int]] = []
    for match in POINT_LABEL.finditer(text):
        if mask[match.start()]:
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end < 0:
            line_end = len(text)
        before = text[line_start : match.start()]
        after = text[match.end() : line_end]
        if _MATH_OPERATOR_SUFFIX.search(before) or _MATH_OPERATOR_PREFIX.match(after):
            continue
        if match.group().startswith("(") and _IMPLICIT_FACTOR.match(after):
            continue
        has_before = bool(_WORD.search(before))
        has_after = bool(_WORD.search(after))
        if has_before and has_after:
            continue
        if points_line(text[line_start:line_end]):
            spans.append((match.start(), match.end()))
            continue
        if has_after:
            if not before.strip():
                spans.append((match.start(), match.end()))
            continue
        if _SENTENCE_END.search(before) or not after.strip():
            spans.append((match.start(), match.end()))
    return tuple(spans)
