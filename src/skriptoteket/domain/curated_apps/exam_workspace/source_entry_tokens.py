"""The one folded source-token index every entry alignment walks.

Exact copying, rewrites and duplicate wording all compare the same folded token
sequence, so the alignment never needs a second representation or a separate
exact-copy route. Character spans stay attached so an aligned token interval can
be projected back onto the source text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class SourceToken:
    """One source token: its character span and its folded comparison form."""

    start: int
    end: int
    folded: str


def source_tokens(text: str) -> tuple[SourceToken, ...]:
    """Index the source once, in order, without a cap or a fallback path."""
    return tuple(
        SourceToken(match.start(), match.end(), match.group().casefold())
        for match in _TOKEN.finditer(text)
    )


def wording_tokens(text: str) -> tuple[str, ...]:
    """The folded token sequence one produced wording aligns by."""
    return tuple(match.group().casefold() for match in _TOKEN.finditer(text))
