"""Quote context for structural source labels, never content deletion rules."""

from __future__ import annotations

_QUOTE_PAIRS = {
    '"': '"',
    "'": "'",
    "“": "”",
    "”": "”",
    "‘": "’",
    "`": "`",
    "«": "»",
    "‹": "›",
}
_APOSTROPHES = ("'",)


def quoted_mask(text: str) -> tuple[bool, ...]:
    """Whether each character lies inside a completed quoted phrase.

    An open phrase closes at its matching quote even after a letter, so a
    single-quoted phrase round-trips while an apostrophe inside a word opens
    nothing. The Swedish right double quote opens a phrase as well as closing
    one. An unmatched delimiter, such as the inch mark in ``5\"``, masks
    nothing. This context disambiguates recovered labels, not emitted text.
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
