"""QTI 2.1 inline prompt rendering for Exam.net-oriented assessment items.

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
    ExamNetQtiImageResource,
    ExamNetQtiItem,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptSegment,
    ExamNetQtiPromptText,
    ExamNetQtiTextEntryGap,
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
    text: str,
) -> ElementTree.Element | None:
    """Append one text run after ``tail_target``, rendering its line breaks as ``br`` elements."""

    lines = text.split("\n")
    tail_target = _append_run_text(parent, tail_target, lines[0])
    for line in lines[1:]:
        tail_target = ElementTree.SubElement(parent, qti_tag("br"))
        tail_target = _append_run_text(parent, tail_target, line)
    return tail_target


def _append_run_text(
    parent: ElementTree.Element,
    tail_target: ElementTree.Element | None,
    text: str,
) -> ElementTree.Element | None:
    if not text:
        return tail_target
    if tail_target is None:
        parent.text = (parent.text or "") + text
    else:
        tail_target.tail = (tail_target.tail or "") + text
    return tail_target


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
    if not 0 <= gap_index < len(item.text_entry_gaps):
        raise ValueError(f"Item {item.item_id} prompt gap index {gap_index} has no text-entry gap.")
    gap = item.text_entry_gaps[gap_index]
    return ElementTree.SubElement(
        parent,
        qti_tag("textEntryInteraction"),
        {
            "responseIdentifier": gap.response_identifier,
            "expectedLength": _expected_text_entry_length(gap),
        },
    )


def append_interaction_prompt(
    interaction: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    prompt = ElementTree.SubElement(interaction, qti_tag("prompt"))
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
        for segments in item.prompt_paragraphs:
            paragraph = ElementTree.SubElement(item_body, qti_tag("p"))
            _append_prompt_segments(paragraph, item, segments, image_paths)
    else:
        for line in normalized_prompt_lines(item.instruction_lines):
            ElementTree.SubElement(item_body, qti_tag("p")).text = line


def _append_prompt_paragraphs(
    prompt: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    """Render rich paragraphs: one stays directly in ``prompt``, several get ``p`` children."""

    if len(item.prompt_paragraphs) == 1:
        _append_prompt_segments(prompt, item, item.prompt_paragraphs[0], image_paths)
        return
    for segments in item.prompt_paragraphs:
        paragraph = ElementTree.SubElement(prompt, qti_tag("p"))
        _append_prompt_segments(paragraph, item, segments, image_paths)


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
            tail_target = _append_prompt_text(parent, tail_target, segment.text)
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
    for segments in item.prompt_paragraphs:
        paragraph = ElementTree.SubElement(parent, qti_tag("p"))
        for gap_index in _append_prompt_segments(paragraph, item, segments, image_paths):
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
        qti_tag("textEntryInteraction"),
        {
            "responseIdentifier": gap.response_identifier,
            "expectedLength": _expected_text_entry_length(gap),
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
                qti_tag("textEntryInteraction"),
                {
                    "responseIdentifier": gap.response_identifier,
                    "expectedLength": _expected_text_entry_length(gap),
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
