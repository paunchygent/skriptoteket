"""A source paragraph of underscores is answer space, not question text (W10).

Purpose:
    W10 keeps the printed answer line out of an imported question. The model-driven build
    drops the model's answer-line paragraph, but the source side still indexes that
    paragraph. When its source runs carry marks, source-format coverage sees the
    unrepresented marked characters and ``SourceFormatting.rebuild_body`` restores the
    paragraph, so the accepted body ends in the paper answer line again. This module owns
    the one source-side answer-space rule both restoring paths apply.

    A source paragraph is answer space when its whole wording is whitespace and
    underscores, it holds at least one underscore, and it carries no picture. The gap
    condition belongs to the caller: a standalone gap paragraph must survive (W6), so the
    caller treats a paragraph as answer space only when no gap lands inside it.

Relationships:
    - ``is_answer_line_text`` is the single owner of the whitespace-and-underscore wording
      rule; ``shared_body.is_printed_answer_line`` reads it for the producer side.
    - ``is_answer_space_paragraph`` is applied by ``SourceFormatting.rebuild_body`` and
      ``source_format_coverage.complete_source_formatting``, the two paths that restore
      source text.
"""

from __future__ import annotations

import re
from collections.abc import Collection

# A paragraph of nothing but whitespace and underscores, holding at least one underscore.
_ANSWER_LINE_TEXT = re.compile(r"[\s_]*_[\s_]*")


def is_answer_line_text(text: str) -> bool:
    """True when ``text`` is only whitespace and underscores and holds an underscore (W10)."""
    return _ANSWER_LINE_TEXT.fullmatch(text) is not None


def is_answer_space_paragraph(
    text: str, start: int, end: int, picture_offsets: Collection[int]
) -> bool:
    """True when the source paragraph ``text[start:end]`` is answer space (W10).

    The paragraph holds only whitespace and underscores with at least one underscore, and
    no picture stands inside ``[start, end)``. The caller has already placed no gap inside
    it, so a standalone gap paragraph never becomes answer space here.
    """
    return is_answer_line_text(text[start:end]) and not any(
        start <= offset < end for offset in picture_offsets
    )
