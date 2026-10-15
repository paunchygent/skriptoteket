"""Printed ordinal occurrences as optional zero-cost alignment prefixes.

A label is never reserved source: the alignment consumes it only when an entry
starts there, so a quoted or literal ordinal stays ordinary content and the
same label cannot be claimed twice. Numeric/alphabetic side conventions remain
soft preferences; actual wording evidence outranks them.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_carrier_context import quoted_mask
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_tokens import SourceToken
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    _ORDINAL_FAMILIES,
    _ordinal_token,
    entry_label_end,
)

_TOKEN = re.compile(r"(?<!\S)[([{]?(?P<token>[A-Za-z0-9]+)[)\]}.:;\-–—]+\s*")


@dataclass(frozen=True)
class LabelOption:
    """One printed ordinal an entry may adopt as a zero-cost anchor prefix."""

    ordinal: int
    start: int
    first_token: int
    token_count: int


def entry_literal_mask(text: str) -> tuple[bool, ...]:
    """Quoted text and point notation cannot supply a printed entry ordinal.

    In particular, the ``p)`` in ``(2 p)`` is a unit or an operand, not the
    sixteenth alphabetic entry. Shared quote context decides which delimiters
    open a literal phrase, so ordinary quoted content stays content.
    """
    mask = list(quoted_mask(text))
    for match in POINT_LABEL.finditer(text):
        mask[match.start() : match.end()] = [True] * (match.end() - match.start())
    return tuple(mask)


def label_options(
    text: str,
    sequences: tuple[str, ...],
    texts: tuple[tuple[str, ...], ...],
    tokens: tuple[SourceToken, ...],
    *,
    blocked: tuple[tuple[int, int], ...] = (),
) -> dict[tuple[int, int], tuple[LabelOption, ...]]:
    """Every printed ordinal occurrence each entry may start from.

    The index visits token boundaries once. An ambiguous spelling such as
    ``I.`` offers its ordinal to every matching family, and wording evidence
    decides which entry adopts it. A label whose first source token is blocked
    or literal is never an anchor.
    """
    ordinals: dict[str, set[int]] = {}
    for ordinal in range(1, max(map(len, texts), default=0) + 1):
        for family in _ORDINAL_FAMILIES:
            token_text = _ordinal_token(family, ordinal)
            if token_text is not None:
                ordinals.setdefault(token_text, set()).add(ordinal)
    mask = entry_literal_mask(text)
    starts = [token.start for token in tokens]
    return_result: dict[tuple[int, int], list[LabelOption]] = {}
    for match in _TOKEN.finditer(text):
        start = match.start()
        if mask[start] or any(a <= start < b for a, b in blocked):
            continue
        for ordinal in sorted(ordinals.get(match.group("token"), ())):
            size = entry_label_end(match.group(), ordinal)
            if size is None:
                continue
            label_end = start + size
            while label_end > start and text[label_end - 1].isspace():
                label_end -= 1
            first_token = bisect_left(starts, start)
            token_count = bisect_left(starts, label_end) - first_token
            if token_count <= 0:
                continue
            for index, surface in enumerate(texts):
                if ordinal > len(surface):
                    continue
                return_result.setdefault((index, ordinal), []).append(
                    LabelOption(
                        ordinal=ordinal,
                        start=start,
                        first_token=first_token,
                        token_count=token_count,
                    )
                )
    return {key: tuple(options) for key, options in return_result.items()}
