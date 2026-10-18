"""Read rich QTI 3.0 content back into the export's prompt-paragraph values.

Purpose:
    Invert the rich-content rendering owned by `examnet_qti_rich_text` and
    `examnet_qti_inline_prompt`: given parsed ``p``/``h1``-``h3`` blocks, marked
    text, line breaks, images and gap interactions, return the
    ``ExamNetQtiPromptParagraph`` values the export started from, up to HTML
    whitespace normalization. Content the export never writes fails closed with
    `ExamNetQtiUnsupportedContent` so the item reader can skip the item.

Relationships:
    - Consumes the prompt value objects of `examnet_qti_contracts`.
    - Reads elements produced by `examnet_qti_rich_text` and
      `examnet_qti_inline_prompt`; never parses bytes itself.
    - Used by the QTI item reader to rebuild prompts, gap-fill bodies and
      choice text from a parsed package.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptSegment,
    ExamNetQtiPromptText,
    ExamNetQtiTextMark,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_rich_text import (
    MARK_RENDER_ORDER,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE

__all__ = [
    "ExamNetQtiReadBody",
    "ExamNetQtiUnsupportedContent",
    "paragraphs_plain_text",
    "read_rich_content",
    "read_text_paragraphs",
]

_BLOCK_HEADING_LEVELS: dict[str, Literal[1, 2, 3] | None] = {
    "p": None,
    "h1": 1,
    "h2": 2,
    "h3": 3,
}
_MARK_LOCAL_NAMES: dict[str, ExamNetQtiTextMark] = {
    "strong": "bold",
    "b": "bold",
    "em": "italic",
    "i": "italic",
    "u": "underline",
    "sup": "superscript",
    "sub": "subscript",
}
_GAP_LOCAL_NAMES = frozenset({"qti-text-entry-interaction", "qti-inline-choice-interaction"})
_WHITESPACE_CHARACTERS = " \t\n\r\f\v"
_QTI_TAG_PREFIX = f"{{{QTI_NAMESPACE}}}"


class ExamNetQtiUnsupportedContent(Exception):
    """Raised for content the import does not map; the item reader turns it into a skipped item."""


@dataclass(frozen=True)
class ExamNetQtiReadBody:
    """One read run: its paragraphs plus the image and gap elements in placement order."""

    paragraphs: tuple[ExamNetQtiPromptParagraph, ...]
    image_elements: tuple[ElementTree.Element, ...]
    gap_elements: tuple[ElementTree.Element, ...]


def read_rich_content(
    nodes: Sequence[ElementTree.Element],
    *,
    leading_text: str | None = None,
    image_offset: int = 0,
    gap_offset: int = 0,
) -> ExamNetQtiReadBody:
    """Read a run of sibling nodes plus the text before the first of them."""

    state = _ReadState(image_offset=image_offset, gap_offset=gap_offset)
    paragraphs = _read_run(leading_text, nodes, state, allow_images_and_gaps=True)
    return ExamNetQtiReadBody(
        paragraphs=paragraphs,
        image_elements=tuple(state.image_elements),
        gap_elements=tuple(state.gap_elements),
    )


def read_text_paragraphs(
    element: ElementTree.Element,
) -> tuple[ExamNetQtiPromptParagraph, ...]:
    """Read a choice-like element's own text and children; images and gaps fail closed."""

    state = _ReadState(image_offset=0, gap_offset=0)
    return _read_run(element.text, list(element), state, allow_images_and_gaps=False)


def paragraphs_plain_text(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> str:
    """Render paragraphs as one plain line each; a gap reads as ``[___]``."""

    lines: list[str] = []
    for paragraph in paragraphs:
        parts: list[str] = []
        for segment in paragraph.segments:
            if isinstance(segment, ExamNetQtiPromptText):
                parts.append(segment.text)
            elif isinstance(segment, ExamNetQtiPromptGap):
                parts.append("[___]")
        lines.append(" ".join("".join(parts).split()))
    return "\n".join(lines).strip()


@dataclass
class _ReadState:
    image_offset: int
    gap_offset: int
    image_elements: list[ElementTree.Element] = field(default_factory=list)
    gap_elements: list[ElementTree.Element] = field(default_factory=list)

    def place_image(self, element: ElementTree.Element) -> int:
        index = self.image_offset + len(self.image_elements)
        self.image_elements.append(element)
        return index

    def place_gap(self, element: ElementTree.Element) -> int:
        index = self.gap_offset + len(self.gap_elements)
        self.gap_elements.append(element)
        return index


@dataclass
class _RawSegment:
    kind: Literal["text", "newline", "image", "gap"]
    text: str = ""
    marks: tuple[ExamNetQtiTextMark, ...] = ()
    index: int = -1


class _ParagraphCollector:
    """Accumulate one paragraph's raw segments before normalization."""

    def __init__(self, heading_level: Literal[1, 2, 3] | None) -> None:
        self._heading_level = heading_level
        self._items: list[_RawSegment] = []

    def add_text(self, text: str, marks: frozenset[ExamNetQtiTextMark]) -> None:
        if _is_indentation(text):
            return
        collapsed = _collapse_whitespace(text)
        if not collapsed:
            return
        self._items.append(_RawSegment(kind="text", text=collapsed, marks=_ordered_marks(marks)))

    def add_newline(self) -> None:
        self._items.append(_RawSegment(kind="newline"))

    def add_image(self, index: int) -> None:
        self._items.append(_RawSegment(kind="image", index=index))

    def add_gap(self, index: int) -> None:
        self._items.append(_RawSegment(kind="gap", index=index))

    def build(self) -> ExamNetQtiPromptParagraph:
        items = _normalize(self._items)
        segments: list[ExamNetQtiPromptSegment] = []
        for item in items:
            if item.kind == "text":
                segments.append(ExamNetQtiPromptText(item.text, item.marks))
            elif item.kind == "newline":
                segments.append(ExamNetQtiPromptText("\n"))
            elif item.kind == "image":
                segments.append(ExamNetQtiPromptImage(item.index))
            else:
                segments.append(ExamNetQtiPromptGap(item.index))
        return ExamNetQtiPromptParagraph(tuple(segments), self._heading_level)


def _read_run(
    leading_text: str | None,
    nodes: Sequence[ElementTree.Element],
    state: _ReadState,
    *,
    allow_images_and_gaps: bool,
) -> tuple[ExamNetQtiPromptParagraph, ...]:
    paragraphs: list[ExamNetQtiPromptParagraph] = []
    implicit: _ParagraphCollector | None = None

    def implicit_collector() -> _ParagraphCollector:
        nonlocal implicit
        if implicit is None:
            implicit = _ParagraphCollector(None)
        return implicit

    def flush_implicit() -> None:
        nonlocal implicit
        if implicit is None:
            return
        paragraph = implicit.build()
        if paragraph.segments:
            paragraphs.append(paragraph)
        implicit = None

    if leading_text:
        implicit_collector().add_text(leading_text, frozenset())

    for node in nodes:
        local_name = _qti_local_name(node)
        if local_name in _BLOCK_HEADING_LEVELS:
            flush_implicit()
            paragraph = _ParagraphCollector(_BLOCK_HEADING_LEVELS[local_name])
            _read_inline_sequence(
                node.text, list(node), frozenset(), paragraph, state, allow_images_and_gaps
            )
            paragraphs.append(paragraph.build())
        else:
            _read_inline_node(node, frozenset(), implicit_collector(), state, allow_images_and_gaps)
        if node.tail:
            implicit_collector().add_text(node.tail, frozenset())

    flush_implicit()
    return tuple(paragraphs)


def _read_inline_sequence(
    leading_text: str | None,
    nodes: Sequence[ElementTree.Element],
    marks: frozenset[ExamNetQtiTextMark],
    collector: _ParagraphCollector,
    state: _ReadState,
    allow_images_and_gaps: bool,
) -> None:
    if leading_text:
        collector.add_text(leading_text, marks)
    for node in nodes:
        _read_inline_node(node, marks, collector, state, allow_images_and_gaps)
        if node.tail:
            collector.add_text(node.tail, marks)


def _read_inline_node(
    node: ElementTree.Element,
    marks: frozenset[ExamNetQtiTextMark],
    collector: _ParagraphCollector,
    state: _ReadState,
    allow_images_and_gaps: bool,
) -> None:
    local_name = _qti_local_name(node)
    mark = _MARK_LOCAL_NAMES.get(local_name)
    if mark is not None:
        _read_inline_sequence(
            node.text, list(node), marks | {mark}, collector, state, allow_images_and_gaps
        )
        return
    if local_name == "span":
        _read_inline_sequence(node.text, list(node), marks, collector, state, allow_images_and_gaps)
        return
    if local_name == "br":
        collector.add_newline()
        return
    if local_name == "img":
        if not allow_images_and_gaps:
            raise ExamNetQtiUnsupportedContent(f"unsupported element {local_name}")
        collector.add_image(state.place_image(node))
        return
    if local_name in _GAP_LOCAL_NAMES:
        if not allow_images_and_gaps:
            raise ExamNetQtiUnsupportedContent(f"unsupported element {local_name}")
        collector.add_gap(state.place_gap(node))
        return
    raise ExamNetQtiUnsupportedContent(f"unsupported element {local_name}")


def _qti_local_name(element: ElementTree.Element) -> str:
    tag = element.tag
    if not isinstance(tag, str):
        raise ExamNetQtiUnsupportedContent("unsupported node in QTI content")
    if not tag.startswith(_QTI_TAG_PREFIX):
        raise ExamNetQtiUnsupportedContent(f"unsupported element {_local_name(tag)}")
    return tag[len(_QTI_TAG_PREFIX) :]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _is_indentation(text: str) -> bool:
    """True for the whitespace-only strings ``ElementTree.indent`` inserts.

    ``indent`` only ever adds whitespace that contains a newline; such text is
    XML pretty-printing, never content. A plain ``" "`` without a newline can
    still be a real space run, so it is kept.
    """

    return "\n" in text and not text.strip()


def _collapse_whitespace(text: str) -> str:
    collapsed: list[str] = []
    in_whitespace = False
    for character in text:
        if character in _WHITESPACE_CHARACTERS:
            in_whitespace = True
        else:
            if in_whitespace:
                collapsed.append(" ")
                in_whitespace = False
            collapsed.append(character)
    if in_whitespace:
        collapsed.append(" ")
    return "".join(collapsed)


def _ordered_marks(marks: frozenset[ExamNetQtiTextMark]) -> tuple[ExamNetQtiTextMark, ...]:
    return tuple(mark for mark in MARK_RENDER_ORDER if mark in marks)


def _normalize(items: list[_RawSegment]) -> list[_RawSegment]:
    trimmed = _trim(items)
    merged = _merge_adjacent_text(_merge_newline_runs(trimmed))
    return merged


def _trim(items: list[_RawSegment]) -> list[_RawSegment]:
    if items and items[0].kind == "text":
        items[0].text = items[0].text.lstrip(" ")
    if items and items[-1].kind == "text":
        items[-1].text = items[-1].text.rstrip(" ")
    for position, item in enumerate(items):
        if item.kind != "newline":
            continue
        if position > 0 and items[position - 1].kind == "text":
            items[position - 1].text = items[position - 1].text.rstrip(" ")
        if position + 1 < len(items) and items[position + 1].kind == "text":
            items[position + 1].text = items[position + 1].text.lstrip(" ")
    return [item for item in items if not (item.kind == "text" and item.text == "")]


def _merge_newline_runs(items: list[_RawSegment]) -> list[_RawSegment]:
    while True:
        merged: list[_RawSegment] = []
        position = 0
        changed = False
        while position < len(items):
            if _is_mergeable_newline_triple(items, position):
                first, _, last = items[position], items[position + 1], items[position + 2]
                merged.append(
                    _RawSegment(
                        kind="text",
                        text=f"{first.text}\n{last.text}",
                        marks=first.marks,
                    )
                )
                position += 3
                changed = True
            else:
                merged.append(items[position])
                position += 1
        items = merged
        if not changed:
            return items


def _is_mergeable_newline_triple(items: list[_RawSegment], position: int) -> bool:
    if position + 2 >= len(items):
        return False
    first, middle, last = items[position], items[position + 1], items[position + 2]
    return (
        first.kind == "text"
        and middle.kind == "newline"
        and last.kind == "text"
        and bool(first.marks)
        and first.marks == last.marks
    )


def _merge_adjacent_text(items: list[_RawSegment]) -> list[_RawSegment]:
    merged: list[_RawSegment] = []
    for item in items:
        if item.kind == "text" and merged:
            previous = merged[-1]
            if previous.kind == "text" and previous.marks == item.marks:
                previous.text = previous.text + item.text
                continue
        merged.append(item)
    return merged
