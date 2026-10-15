"""Safe QTI element rendering for text marks, paragraphs and heading levels.

Purpose:
    Wrap text runs in the semantic inline elements Exam.net renders
    (``strong``, ``em``, ``u``, ``sup``, ``sub``) and place paragraphs as
    ``h1``-``h3`` or ``p``. Marks and heading levels always become real XML
    elements; no renderer ever writes markup as raw HTML text.

Relationships:
    - Consumes the prompt value objects of `examnet_qti_contracts`.
    - Used by `examnet_qti_inline_prompt` (prompts, shared instructions,
      gap-fill bodies) and by `examnet_qti_xml` (choice and match entries),
      so neither renderer imports the other.
"""

from __future__ import annotations

from types import MappingProxyType
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptText,
    ExamNetQtiTextMark,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import qti_tag

MARK_ELEMENT_NAMES = MappingProxyType(
    {
        "bold": "strong",
        "italic": "em",
        "underline": "u",
        "superscript": "sup",
        "subscript": "sub",
    }
)

MARK_RENDER_ORDER: tuple[ExamNetQtiTextMark, ...] = (
    "bold",
    "italic",
    "underline",
    "superscript",
    "subscript",
)


def append_marked_text(
    parent: ElementTree.Element,
    tail_target: ElementTree.Element | None,
    text: str,
    marks: tuple[ExamNetQtiTextMark, ...] = (),
) -> ElementTree.Element | None:
    """Append one text run after ``tail_target``, wrapped in its mark elements.

    Line breaks render as ``br`` elements like the unmarked renderer, and the
    returned element is the run's outermost mark element, so the caller's next
    run follows it.
    """

    lines = text.split("\n")
    tail_target = _append_marked_line(parent, tail_target, lines[0], marks)
    for line in lines[1:]:
        tail_target = ElementTree.SubElement(parent, qti_tag("br"))
        tail_target = _append_marked_line(parent, tail_target, line, marks)
    return tail_target


def paragraph_element(
    parent: ElementTree.Element,
    heading_level: int | None,
) -> ElementTree.Element:
    """Append the paragraph the content belongs to: ``h1``-``h3`` or ``p``."""

    if heading_level is None:
        return ElementTree.SubElement(parent, qti_tag("p"))
    if heading_level not in (1, 2, 3):
        raise ValueError(f"heading level {heading_level} is outside h1-h3")
    return ElementTree.SubElement(parent, qti_tag(f"h{heading_level}"))


def append_textual_paragraphs(
    parent: ElementTree.Element,
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
) -> None:
    """Render text-only paragraphs; a choice or match entry holds no interaction.

    A gap or image segment there fails closed instead of nesting an interaction
    inside the choice.
    """

    for paragraph in paragraphs:
        element = paragraph_element(parent, paragraph.heading_level)
        tail_target: ElementTree.Element | None = None
        for segment in paragraph.segments:
            if not isinstance(segment, ExamNetQtiPromptText):
                raise ValueError("a choice or match entry renders text paragraphs only")
            tail_target = append_marked_text(element, tail_target, segment.text, segment.marks)


def _append_marked_line(
    parent: ElementTree.Element,
    tail_target: ElementTree.Element | None,
    text: str,
    marks: tuple[ExamNetQtiTextMark, ...],
) -> ElementTree.Element | None:
    if not text:
        return tail_target
    ordered_marks = _ordered_marks(marks)
    if not ordered_marks:
        return _append_run_text(parent, tail_target, text)
    # Each successive wrapper nests inside the previous one; the innermost holds text
    # and the outermost stays the tail target for the paragraph's next run.
    outer = ElementTree.SubElement(parent, qti_tag(MARK_ELEMENT_NAMES[ordered_marks[0]]))
    inner = outer
    for mark in ordered_marks[1:]:
        inner = ElementTree.SubElement(inner, qti_tag(MARK_ELEMENT_NAMES[mark]))
    inner.text = (inner.text or "") + text
    return outer


def _append_run_text(
    parent: ElementTree.Element,
    tail_target: ElementTree.Element | None,
    text: str,
) -> ElementTree.Element | None:
    if tail_target is None:
        parent.text = (parent.text or "") + text
    else:
        tail_target.tail = (tail_target.tail or "") + text
    return tail_target


def _ordered_marks(marks: tuple[ExamNetQtiTextMark, ...]) -> tuple[ExamNetQtiTextMark, ...]:
    unknown = tuple(mark for mark in marks if mark not in MARK_RENDER_ORDER)
    if unknown:
        raise ValueError(f"unknown text marks: {unknown}")
    if len(set(marks)) != len(marks):
        raise ValueError("text marks must not repeat")
    if "superscript" in marks and "subscript" in marks:
        raise ValueError("superscript and subscript cannot apply to the same text run")
    return tuple(mark for mark in MARK_RENDER_ORDER if mark in marks)
