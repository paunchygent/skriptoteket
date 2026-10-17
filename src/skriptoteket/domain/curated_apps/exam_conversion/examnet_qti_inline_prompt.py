"""QTI 3.0 inline prompt rendering for Exam.net-oriented assessment items.

Purpose:
    Render one item's inline content: interaction prompts and rich gap-fill
    bodies with ordered text runs, line breaks, paragraph boundaries, images
    and text-entry gaps at their source position, plus the positionless
    fallback for items without rich paragraphs.

Relationships:
    - Consumes `domain.examnet_qti_contracts` item value objects.
    - Names elements through `domain.examnet_qti_terms`, which
      `domain.examnet_qti_xml` also re-exports for declarations, scoring and
      interaction assembly.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiImageResource,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptSegment,
    ExamNetQtiPromptText,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_rich_text import (
    append_marked_text,
    paragraph_element,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import qti_tag

__all__ = [
    "append_gap_fill_body",
    "append_images",
    "append_inline_gap_fill_paragraphs",
    "append_interaction_prompt",
    "normalized_prompt_lines",
]

_GAP_MARKER_PATTERN = re.compile(r"(?:\[_+\]|_{3,})")


def _append_prompt_text(
    parent: ElementTree.Element,
    tail_target: ElementTree.Element | None,
    segment: ExamNetQtiPromptText,
) -> ElementTree.Element | None:
    """Append one text run, rendering its marks and line breaks as elements."""

    return append_marked_text(parent, tail_target, segment.text, segment.marks)


def _append_prompt_image(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
    image_index: int,
) -> ElementTree.Element:
    if not 0 <= image_index < len(item.image_resources):
        raise ValueError(
            f"Item {item.item_id} prompt image index {image_index} has no image resource."
        )
    if len(image_paths) != len(item.image_resources):
        raise ValueError(f"Item {item.item_id} needs one packaged path per image resource.")
    image = item.image_resources[image_index]
    return ElementTree.SubElement(
        parent,
        qti_tag("img"),
        {
            "src": image_paths[image_index],
            "alt": image.alt_text,
        },
    )


def _append_prompt_gap(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    gap_index: int,
) -> ElementTree.Element:
    if not 0 <= gap_index < len(item.response_gaps):
        raise ValueError(f"Item {item.item_id} prompt gap index {gap_index} has no text-entry gap.")
    gap = item.response_gaps[gap_index]
    if isinstance(gap, ExamNetQtiInlineChoiceGap):
        interaction = ElementTree.SubElement(
            parent,
            qti_tag("qti-inline-choice-interaction"),
            {"response-identifier": gap.response_identifier, "shuffle": "false"},
        )
        for option in gap.options:
            choice = ElementTree.SubElement(
                interaction, qti_tag("qti-inline-choice"), {"identifier": option.identifier}
            )
            _append_inline_choice_content(choice, option)
        return interaction
    return ElementTree.SubElement(
        parent,
        qti_tag("qti-text-entry-interaction"),
        {
            "response-identifier": gap.response_identifier,
            "expected-length": _expected_text_entry_length(gap),
        },
    )


def _append_inline_choice_content(choice: ElementTree.Element, option: ExamNetQtiChoice) -> None:
    """Render static inline content, never block paragraphs or interactions.

    Paragraph boundaries become line breaks; headings cannot be represented by
    inline-choice content and fail closed instead of silently losing formatting.
    """
    if not option.body:
        choice.text = option.text
        return
    tail_target: ElementTree.Element | None = None
    for index, paragraph in enumerate(option.body):
        if paragraph.heading_level is not None:
            raise ValueError("inline-choice options cannot render heading levels")
        if index:
            tail_target = ElementTree.SubElement(choice, qti_tag("br"))
        for segment in paragraph.segments:
            if not isinstance(segment, ExamNetQtiPromptText):
                raise ValueError("inline-choice options render text segments only")
            tail_target = append_marked_text(choice, tail_target, segment.text, segment.marks)


def append_interaction_prompt(
    interaction: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    prompt = ElementTree.SubElement(interaction, qti_tag("qti-prompt"))
    if item.prompt_paragraphs:
        _append_prompt_paragraphs(prompt, item, image_paths)
        return
    lines = normalized_prompt_lines(item.prompt_lines)
    if len(lines) == 1:
        prompt.text = lines[0]
    else:
        for line in lines:
            paragraph = ElementTree.SubElement(prompt, qti_tag("p"))
            paragraph.text = line
    for image, image_path in zip(item.image_resources, image_paths, strict=True):
        ElementTree.SubElement(
            prompt,
            qti_tag("img"),
            {
                "src": image_path,
                "alt": image.alt_text,
            },
        )


def append_shared_instruction_body(
    item_body: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    """Place the parent stem once, before child interactions, using its own carriers."""
    if item.prompt_paragraphs:
        for paragraph in item.prompt_paragraphs:
            element = paragraph_element(item_body, paragraph.heading_level)
            _append_prompt_segments(element, item, paragraph.segments, image_paths)
    else:
        for line in normalized_prompt_lines(item.instruction_lines):
            ElementTree.SubElement(item_body, qti_tag("p")).text = line


def _append_prompt_paragraphs(
    prompt: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    """Render rich paragraphs: one plain stays directly in ``prompt``, others get children."""

    paragraphs = item.prompt_paragraphs
    if len(paragraphs) == 1 and paragraphs[0].heading_level is None:
        _append_prompt_segments(prompt, item, paragraphs[0].segments, image_paths)
        return
    for paragraph in paragraphs:
        element = paragraph_element(prompt, paragraph.heading_level)
        _append_prompt_segments(element, item, paragraph.segments, image_paths)


def _append_prompt_segments(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    segments: tuple[ExamNetQtiPromptSegment, ...],
    image_paths: tuple[str, ...],
) -> tuple[int, ...]:
    """Append rich segments in order; return the gap indexes they place."""

    placed_gap_indexes: list[int] = []
    tail_target: ElementTree.Element | None = None
    for segment in segments:
        if isinstance(segment, ExamNetQtiPromptText):
            tail_target = _append_prompt_text(parent, tail_target, segment)
        elif isinstance(segment, ExamNetQtiPromptImage):
            tail_target = _append_prompt_image(parent, item, image_paths, segment.image_index)
        elif isinstance(segment, ExamNetQtiPromptGap):
            tail_target = _append_prompt_gap(parent, item, segment.gap_index)
            placed_gap_indexes.append(segment.gap_index)
        else:
            raise ValueError(f"Item {item.item_id} carries an unknown prompt segment.")
    return tuple(placed_gap_indexes)


def normalized_prompt_lines(prompt_lines: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        normalized for normalized in (" ".join(line.split()) for line in prompt_lines) if normalized
    )


def append_images(
    parent: ElementTree.Element,
    images: tuple[ExamNetQtiImageResource, ...],
    image_paths: tuple[str, ...],
) -> None:
    for image, image_path in zip(images, image_paths, strict=True):
        paragraph = ElementTree.SubElement(parent, qti_tag("p"))
        ElementTree.SubElement(
            paragraph,
            qti_tag("img"),
            {
                "src": image_path,
                "alt": image.alt_text,
            },
        )


def append_gap_fill_body(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    if item.interaction_type is ExamNetQtiInteractionType.INLINE_CHOICE:
        placed = append_inline_gap_fill_paragraphs(parent, item, image_paths)
        if placed != frozenset(range(len(item.inline_choice_gaps))):
            raise ValueError("inline_choice body must place every gap exactly once")
        return
    if item.prompt_paragraphs:
        placed_gap_indexes = append_inline_gap_fill_paragraphs(parent, item, image_paths)
        for index, gap in enumerate(item.text_entry_gaps):
            if index not in placed_gap_indexes:
                _append_labeled_gap(parent, gap)
        return
    gaps = iter(item.text_entry_gaps)
    used_count = 0
    for line in _expanded_prompt_lines(item.prompt_lines):
        used_count += _append_gap_prompt_line(parent, line, gaps)
    for gap in item.text_entry_gaps[used_count:]:
        _append_labeled_gap(parent, gap)


def append_inline_gap_fill_paragraphs(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> frozenset[int]:
    """Render rich item-body paragraphs and return the gap indexes they place."""

    placed_gap_indexes: set[int] = set()
    for paragraph in item.prompt_paragraphs:
        element = paragraph_element(parent, paragraph.heading_level)
        for gap_index in _append_prompt_segments(element, item, paragraph.segments, image_paths):
            if gap_index in placed_gap_indexes:
                raise ValueError(
                    f"Item {item.item_id} places gap index {gap_index} more than once."
                )
            placed_gap_indexes.add(gap_index)
    return frozenset(placed_gap_indexes)


def _append_labeled_gap(parent: ElementTree.Element, gap: ExamNetQtiTextEntryGap) -> None:
    paragraph = ElementTree.SubElement(parent, qti_tag("p"))
    paragraph.text = f"{gap.label}: "
    ElementTree.SubElement(
        paragraph,
        qti_tag("qti-text-entry-interaction"),
        {
            "response-identifier": gap.response_identifier,
            "expected-length": _expected_text_entry_length(gap),
        },
    )


def _expected_text_entry_length(gap: ExamNetQtiTextEntryGap) -> str:
    """Size one text-entry field from its accepted answers, within readable bounds."""

    values = tuple(value.strip() for value in gap.accepted_values if value.strip())
    if not values:
        return "20"
    return str(max(8, min(max(len(value) for value in values), 80)))


def _expanded_prompt_lines(prompt_lines: tuple[str, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for prompt_line in prompt_lines:
        child_lines = tuple(line.strip() for line in prompt_line.splitlines() if line.strip())
        lines.extend(child_lines or (prompt_line,))
    return tuple(lines)


def _append_gap_prompt_line(
    parent: ElementTree.Element,
    line: str,
    gaps: Iterator[ExamNetQtiTextEntryGap],
) -> int:
    paragraph = ElementTree.SubElement(parent, qti_tag("p"))
    consumed = 0
    position = 0
    tail_target: ElementTree.Element | None = None
    for match in _GAP_MARKER_PATTERN.finditer(line):
        text_before_gap = line[position : match.start()]
        if tail_target is None:
            paragraph.text = (paragraph.text or "") + text_before_gap
        else:
            tail_target.tail = (tail_target.tail or "") + text_before_gap
        gap = next(gaps, None)
        if gap is None:
            if tail_target is None:
                paragraph.text = (paragraph.text or "") + match.group(0)
            else:
                tail_target.tail = (tail_target.tail or "") + match.group(0)
        else:
            tail_target = ElementTree.SubElement(
                paragraph,
                qti_tag("qti-text-entry-interaction"),
                {
                    "response-identifier": gap.response_identifier,
                    "expected-length": _expected_text_entry_length(gap),
                },
            )
            consumed += 1
        position = match.end()
    remaining_text = line[position:]
    if tail_target is None:
        paragraph.text = (paragraph.text or "") + remaining_text
    else:
        tail_target.tail = (tail_target.tail or "") + remaining_text
    return consumed
