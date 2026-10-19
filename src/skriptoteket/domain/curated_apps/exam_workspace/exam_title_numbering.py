"""Numbered exam titles for duplicate names in Mina filer."""

from __future__ import annotations

import re
from collections.abc import Collection

_TITLE_SUFFIX_PATTERN = re.compile(r"^(.*) \((\d+)\)$")


def exam_title_base(title: str) -> str:
    """Return the title with one trailing `` (n)`` suffix removed, if any."""
    match = _TITLE_SUFFIX_PATTERN.match(title)
    if match is not None and int(match.group(2)) >= 1:
        return match.group(1)
    return title


def numbered_exam_title(title: str, taken: Collection[str]) -> str:
    """Return ``title`` unchanged when free, else ``base (k)`` for the base.

    ``base`` is the title with one trailing `` (n)`` removed (n a positive
    integer); ``k`` is the smallest integer >= 2 such that ``base (k)`` is
    not taken. Matching is exact string equality against ``taken``.
    """
    if title not in taken:
        return title
    base = exam_title_base(title)
    suffix = 2
    while f"{base} ({suffix})" in taken:
        suffix += 1
    return f"{base} ({suffix})"
