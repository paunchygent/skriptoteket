"""QTI 2.1 element builders for Exam.net-oriented assessment items.

Purpose:
    Build the response declarations, outcomes and interactions of one governed
    Exam.net QTI item without file system or service-route concerns.

Relationships:
    - Consumes `domain.examnet_qti_contracts` item value objects.
    - Used by `examnet_qti_item_xml` for standalone items and for each child of a
      parent item.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from decimal import Decimal
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTextEntryGap,
)

QTI_NAMESPACE = "http://www.imsglobal.org/xsd/imsqti_v2p1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
QTI_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
)
MAP_RESPONSE_TEMPLATE = "http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"
RESPONSE_IDENTIFIER = "RESPONSE"
FREE_TEXT_CRITERION_MAP_KEY = "CRITERION_FULL"
RESPONSE_IDENTIFIER = "RESPONSE"
_GAP_MARKER_PATTERN = re.compile(r"(?:\[_+\]|_{3,})")


def append_response_declaration(
    root: ElementTree.Element,
    item: ExamNetQtiItem,
    response_id: str = RESPONSE_IDENTIFIER,
) -> tuple[str, ...]:
    """Append the item's response declarations; return the ids that carry a mapping."""

    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        declaration = ElementTree.SubElement(
            root,
            qti_tag("responseDeclaration"),
            {
                "identifier": response_id,
                "cardinality": "single",
                "baseType": "string",
            },
        )
        if item.free_text_criterion_points is not None:
            points = str(item.free_text_criterion_points)
            mapping = ElementTree.SubElement(
                declaration,
                qti_tag("mapping"),
                {"defaultValue": "0", "lowerBound": "0", "upperBound": points},
            )
            ElementTree.SubElement(
                mapping,
                qti_tag("mapEntry"),
                {"mapKey": FREE_TEXT_CRITERION_MAP_KEY, "mappedValue": points},
            )
            return (response_id,)
        return ()

    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        gap_point_values = _gap_point_values(item)
        mapped_gap_ids: list[str] = []
        for index, gap in enumerate(item.text_entry_gaps):
            gap_points = None if gap_point_values is None else gap_point_values[index]
            if _append_gap_response_declaration(root, gap, gap_points):
                mapped_gap_ids.append(gap.response_identifier)
        return tuple(mapped_gap_ids)

    cardinality = "multiple"
    base_type = "identifier"
    values: tuple[str, ...]
    if item.interaction_type == ExamNetQtiInteractionType.SINGLE_CHOICE:
        cardinality = "single"
        values = item.correct_choice_identifiers
    elif item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        values = item.correct_choice_identifiers
    else:
        base_type = "directedPair"
        values = tuple(
            f"{pair.left_identifier} {pair.right_identifier}" for pair in item.match_pairs
        )

    declaration = ElementTree.SubElement(
        root,
        qti_tag("responseDeclaration"),
        {
            "identifier": response_id,
            "cardinality": cardinality,
            "baseType": base_type,
        },
    )
    if values:
        correct_response = ElementTree.SubElement(declaration, qti_tag("correctResponse"))
        for value in values:
            value_element = ElementTree.SubElement(correct_response, qti_tag("value"))
            value_element.text = value
    if (
        values
        and item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC
        and item.max_score is not None
    ):
        mapped_values = _split_point_values(item.max_score, len(values))
        mapping = ElementTree.SubElement(
            declaration,
            qti_tag("mapping"),
            {"defaultValue": "0", "lowerBound": "0", "upperBound": str(item.max_score)},
        )
        for value, mapped_value in zip(values, mapped_values, strict=True):
            ElementTree.SubElement(
                mapping,
                qti_tag("mapEntry"),
                {"mapKey": value, "mappedValue": mapped_value},
            )
        return (response_id,)
    return ()


def _append_gap_response_declaration(
    root: ElementTree.Element,
    gap: ExamNetQtiTextEntryGap,
    gap_points: str | None,
) -> bool:
    values = tuple(value.strip() for value in gap.accepted_values if value.strip())
    declaration = ElementTree.SubElement(
        root,
        qti_tag("responseDeclaration"),
        {
            "identifier": gap.response_identifier,
            "cardinality": "single",
            "baseType": "string",
        },
    )
    if not values:
        return False
    correct_response = ElementTree.SubElement(declaration, qti_tag("correctResponse"))
    value_element = ElementTree.SubElement(correct_response, qti_tag("value"))
    value_element.text = values[0]
    if gap_points is None:
        return False
    mapping = ElementTree.SubElement(
        declaration,
        qti_tag("mapping"),
        {"defaultValue": "0", "lowerBound": "0", "upperBound": gap_points},
    )
    for value in values:
        ElementTree.SubElement(
            mapping,
            qti_tag("mapEntry"),
            {"mapKey": value, "mappedValue": gap_points, "caseSensitive": "false"},
        )
    return True


def _gap_point_values(item: ExamNetQtiItem) -> tuple[str, ...] | None:
    if item.max_score is None or not item.text_entry_gaps:
        return None
    return _split_point_values(item.max_score, len(item.text_entry_gaps))


def _split_point_values(total: int | float, count: int) -> tuple[str, ...]:
    decimal_total = Decimal(str(total))
    exponent = decimal_total.as_tuple().exponent
    decimal_places = max(2, -exponent) if isinstance(exponent, int) else 2
    unit = Decimal(1).scaleb(-decimal_places)
    total_units = int(decimal_total / unit)
    while total_units < count:
        decimal_places += 1
        unit = Decimal(1).scaleb(-decimal_places)
        total_units = int(decimal_total / unit)
    base_units, extra_units = divmod(total_units, count)
    return tuple(
        _format_point_units(base_units + (1 if index < extra_units else 0), decimal_places)
        for index in range(count)
    )


def _format_point_units(units: int, decimal_places: int) -> str:
    value = Decimal(units).scaleb(-decimal_places)
    return format(value, "f").rstrip("0").rstrip(".") or "0"


def emits_map_response(item: ExamNetQtiItem) -> bool:
    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        return item.free_text_criterion_points is not None
    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        return False
    return item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC


def append_score_outcome(root: ElementTree.Element, item: ExamNetQtiItem) -> None:
    outcome = ElementTree.SubElement(
        root,
        qti_tag("outcomeDeclaration"),
        {
            "identifier": "SCORE",
            "cardinality": "single",
            "baseType": "float",
        },
    )
    default_value = ElementTree.SubElement(outcome, qti_tag("defaultValue"))
    value = ElementTree.SubElement(default_value, qti_tag("value"))
    value.text = "0"
    max_score = ElementTree.SubElement(
        root,
        qti_tag("outcomeDeclaration"),
        {
            "identifier": "MAXSCORE",
            "cardinality": "single",
            "baseType": "float",
        },
    )
    max_default = ElementTree.SubElement(max_score, qti_tag("defaultValue"))
    max_value = ElementTree.SubElement(max_default, qti_tag("value"))
    max_value.text = str(item.max_score or 0)


def _append_interaction_prompt(
    interaction: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    prompt = ElementTree.SubElement(interaction, qti_tag("prompt"))
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


def append_interaction(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
    response_id: str = RESPONSE_IDENTIFIER,
) -> None:
    if item.interaction_type in {
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    }:
        _append_choice_interaction(parent, item, image_paths, response_id)
        return
    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        interaction = ElementTree.SubElement(
            parent,
            qti_tag("extendedTextInteraction"),
            {
                "responseIdentifier": response_id,
                "expectedLines": "8",
            },
        )
        _append_interaction_prompt(interaction, item, image_paths)
        return
    _append_match_interaction(parent, item, image_paths, response_id)


def append_gap_fill_body(parent: ElementTree.Element, item: ExamNetQtiItem) -> None:
    gaps = iter(item.text_entry_gaps)
    used_count = 0
    for line in _expanded_prompt_lines(item.prompt_lines):
        used_count += _append_gap_prompt_line(parent, line, gaps)
    remaining_gaps = item.text_entry_gaps[used_count:]
    for gap in remaining_gaps:
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


def _expected_text_entry_length(gap: ExamNetQtiTextEntryGap) -> str:
    values = tuple(value.strip() for value in gap.accepted_values if value.strip())
    if not values:
        return "20"
    return str(max(8, min(max(len(value) for value in values), 80)))


def _append_choice_interaction(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
    response_id: str,
) -> None:
    max_choices = "1"
    if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        max_choices = str(len(item.correct_choice_identifiers) or len(item.choices))
    interaction = ElementTree.SubElement(
        parent,
        qti_tag("choiceInteraction"),
        {
            "responseIdentifier": response_id,
            "maxChoices": max_choices,
        },
    )
    _append_interaction_prompt(interaction, item, image_paths)
    for choice in item.choices:
        _append_simple_choice(interaction, choice)


def _append_simple_choice(parent: ElementTree.Element, choice: ExamNetQtiChoice) -> None:
    choice_element = ElementTree.SubElement(
        parent,
        qti_tag("simpleChoice"),
        {"identifier": choice.identifier},
    )
    choice_element.text = choice.text


def _append_match_interaction(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
    response_id: str,
) -> None:
    # Each visible list keeps its own order; the pairing lives only in the response data.
    interaction = ElementTree.SubElement(
        parent,
        qti_tag("matchInteraction"),
        {
            "responseIdentifier": response_id,
            "maxAssociations": str(len(item.match_left)),
        },
    )
    _append_interaction_prompt(interaction, item, image_paths)
    left_set = ElementTree.SubElement(interaction, qti_tag("simpleMatchSet"))
    right_set = ElementTree.SubElement(interaction, qti_tag("simpleMatchSet"))
    for entry in item.match_left:
        _append_associable_choice(left_set, entry.identifier, entry.text)
    for entry in item.match_right:
        _append_associable_choice(right_set, entry.identifier, entry.text)


def _append_associable_choice(parent: ElementTree.Element, identifier: str, text: str) -> None:
    choice = ElementTree.SubElement(
        parent,
        qti_tag("simpleAssociableChoice"),
        {"identifier": identifier, "matchMax": "1"},
    )
    choice.text = text


def qti_tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def xsi_tag(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"
