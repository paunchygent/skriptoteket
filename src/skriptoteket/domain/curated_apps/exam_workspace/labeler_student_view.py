"""Anchored student text and source-shaped keys for the item-type labeler (D14)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    INLINE_ANSWER_MARK,
    POINT_LABEL,
    points_line,
)

ANSWER_SLOT = "[___]"
_KEY_LABEL = re.compile(r"\b(?:Correct\s+answer|Answer|Svar|Facit)\s*:\s*", re.IGNORECASE)
_ACCEPTED_ALTERNATIVES = re.compile(
    r"\(\s*(?:Also\s+accepted|Accept|Även\s+godtas|Godtas\s+även)\s*:[^)]*\)",
    re.IGNORECASE,
)


def _unmarked(text: str) -> str:
    return INLINE_ANSWER_MARK.sub(lambda match: match.group(1), text)


def _without_points(text: str) -> str:
    return "" if points_line(text) else POINT_LABEL.sub("", text).strip()


@dataclass(frozen=True)
class StudentLine:
    """A visible student line with its original source anchor."""

    anchor: str
    text: str


@dataclass(frozen=True)
class StudentView:
    """Student lines in source order and the separate answer key."""

    lines: tuple[StudentLine, ...]
    answer_key: str | None

    @property
    def question(self) -> str:
        """Join visible lines for the labeler input."""
        return "\n".join(line.text for line in self.lines)


def student_view(question: Sequence[DocxChunk], keys: Sequence[DocxChunk]) -> StudentView:
    """Restore inline response slots, retaining each keyed source line once."""
    key_anchors = {chunk.anchor for chunk in keys}
    seen: set[str] = set()
    key_lines: list[str] = []
    lines: list[StudentLine] = []
    for chunk in (*question, *keys):
        if chunk.anchor in seen:
            continue
        seen.add(chunk.anchor)
        text = chunk.marked_text
        inline = INLINE_ANSWER_MARK.search(text) is not None
        if inline or chunk.anchor in key_anchors:
            key_lines.append(_unmarked(text))
        if inline:
            text = _ACCEPTED_ALTERNATIVES.sub("", text)
            visible = _KEY_LABEL.sub("", INLINE_ANSWER_MARK.sub("", text))
            if not _without_points(visible):
                continue
            text = _KEY_LABEL.sub("", INLINE_ANSWER_MARK.sub(ANSWER_SLOT, text))
        elif chunk.anchor in key_anchors:
            continue
        text = _without_points(text)
        if text:
            lines.append(StudentLine(anchor=chunk.anchor, text=text))
    return StudentView(lines=tuple(lines), answer_key="\n".join(key_lines) or None)


def tight_heading(
    chunks: Sequence[DocxChunk], anchors: Sequence[str], excluded_anchors: frozenset[str]
) -> str | None:
    """Return only the nearest preceding heading outside title/question/key ownership."""
    own = set(anchors)
    start = next((i for i, chunk in enumerate(chunks) if chunk.anchor in own), None)
    if start is None:
        return None
    for chunk in reversed(chunks[:start]):
        if chunk.kind == "heading" and chunk.anchor not in excluded_anchors:
            return _without_points(chunk.marked_text) or None
    return None
