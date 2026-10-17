"""QTI 3.0 element builders for Exam.net-oriented assessment items.

Purpose:
    Build the response declarations, outcomes and interactions of one governed
    Exam.net QTI item without file system or service-route concerns.

Relationships:
    - Consumes `domain.examnet_qti_contracts` item value objects.
    - Used by `examnet_qti_item_xml` for standalone items and for each child of a
      parent item.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_inline_prompt import (
    append_interaction_prompt,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_rich_text import (
    append_textual_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    MAP_RESPONSE_TEMPLATE,
    QTI_NAMESPACE,
    QTI_SCHEMA_LOCATION,
    XSI_NAMESPACE,
    qti_tag,
    xsi_tag,
)

RESPONSE_IDENTIFIER = "RESPONSE"
FREE_TEXT_CRITERION_MAP_KEY = "CRITERION_FULL"

__all__ = [
    "FREE_TEXT_CRITERION_MAP_KEY",
    "MAP_RESPONSE_TEMPLATE",
    "QTI_NAMESPACE",
    "QTI_SCHEMA_LOCATION",
    "RESPONSE_IDENTIFIER",
    "XSI_NAMESPACE",
    "append_interaction",
    "append_response_declaration",
    "append_score_outcome",
    "emits_map_response",
    "emits_all_or_nothing",
    "gap_point_values",
    "qti_tag",
    "xsi_tag",
]


def append_response_declaration(
    root: ElementTree.Element,
    item: ExamNetQtiItem,
    response_id: str = RESPONSE_IDENTIFIER,
) -> tuple[str, ...]:
    """Append the item's response declarations; return the ids that carry a mapping."""

    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        declaration = ElementTree.SubElement(
            root,
            qti_tag("qti-response-declaration"),
            {
                "identifier": response_id,
                "cardinality": "single",
                "base-type": "string",
            },
        )
        if item.free_text_criterion_points is not None:
            upper_bound, entries = _free_text_mapping(item)
            mapping = ElementTree.SubElement(
                declaration,
                qti_tag("qti-mapping"),
                {"default-value": "0", "lower-bound": "0", "upper-bound": upper_bound},
            )
            for criterion_map_key, row_value in entries:
                ElementTree.SubElement(
                    mapping,
                    qti_tag("qti-map-entry"),
                    {"map-key": criterion_map_key, "mapped-value": row_value},
                )
            return (response_id,)
        return ()

    if item.interaction_type == ExamNetQtiInteractionType.INLINE_CHOICE:
        gap_values = gap_point_values(item)
        mapped_ids: list[str] = []
        for index, inline_gap in enumerate(item.inline_choice_gaps):
            declaration = ElementTree.SubElement(
                root,
                qti_tag("qti-response-declaration"),
                {
                    "identifier": inline_gap.response_identifier,
                    "cardinality": "single",
                    "base-type": "identifier",
                },
            )
            correct = ElementTree.SubElement(declaration, qti_tag("qti-correct-response"))
            ElementTree.SubElement(
                correct, qti_tag("qti-value")
            ).text = inline_gap.correct_option_identifier
            if gap_values is not None:
                points = gap_values[index]
                mapping = ElementTree.SubElement(
                    declaration,
                    qti_tag("qti-mapping"),
                    {"default-value": "0", "lower-bound": "0", "upper-bound": points},
                )
                ElementTree.SubElement(
                    mapping,
                    qti_tag("qti-map-entry"),
                    {"map-key": inline_gap.correct_option_identifier, "mapped-value": points},
                )
                mapped_ids.append(inline_gap.response_identifier)
        return tuple(mapped_ids)

    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        gap_values = gap_point_values(item)
        mapped_gap_ids: list[str] = []
        for index, gap in enumerate(item.text_entry_gaps):
            gap_points = None if gap_values is None else gap_values[index]
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
        qti_tag("qti-response-declaration"),
        {
            "identifier": response_id,
            "cardinality": cardinality,
            "base-type": base_type,
        },
    )
    if values:
        correct_response = ElementTree.SubElement(declaration, qti_tag("qti-correct-response"))
        for value in values:
            value_element = ElementTree.SubElement(correct_response, qti_tag("qti-value"))
            value_element.text = value
    mapped_value = _equal_choice_point_value(item)
    if values and mapped_value is not None:
        mapping = ElementTree.SubElement(
            declaration,
            qti_tag("qti-mapping"),
            {"default-value": "0", "lower-bound": "0", "upper-bound": str(item.max_score)},
        )
        for value in values:
            ElementTree.SubElement(
                mapping,
                qti_tag("qti-map-entry"),
                {"map-key": value, "mapped-value": mapped_value},
            )
        return (response_id,)
    return ()


def _free_text_mapping(item: ExamNetQtiItem) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Return the free text mapping's upper bound and one entry per rule row.

    Exam.net reads the response mapping and writes one rule row per map entry at
    the entry's own value (probe V110, V126-V128), so a criteria item carries one
    row's value (1) and the item's total (their sum) and is written as one
    1-point row per criterion point (Q13). An item without criteria carries its
    total as the row value, so it stays one row worth its points. Criterion text
    never enters the package; the map keys are opaque and Exam.net replaces them.
    A value-total ratio that is not a positive whole number cannot come from
    either lane and raises instead of encoding a corrupt score.
    """

    value = item.free_text_criterion_points
    if value is None:
        raise ValueError("free text mapping requires a criterion value")
    per_row = Decimal(str(value))
    total = Decimal(str(item.max_score)) if item.max_score is not None else per_row
    if per_row <= 0:
        raise ValueError("free text mapping row value must be positive")
    row_count = total / per_row
    if row_count != row_count.to_integral_value() or row_count < 1:
        raise ValueError("free text mapping rows must be a positive whole number")
    upper_bound = str(item.max_score) if item.max_score is not None else str(value)
    count = int(row_count)
    if count == 1:
        return upper_bound, ((FREE_TEXT_CRITERION_MAP_KEY, str(value)),)
    return upper_bound, tuple(
        (f"CRITERION_{index}", _format_points(per_row)) for index in range(1, count + 1)
    )


def _append_gap_response_declaration(
    root: ElementTree.Element,
    gap: ExamNetQtiTextEntryGap,
    gap_points: str | None,
) -> bool:
    values = tuple(value.strip() for value in gap.accepted_values if value.strip())
    declaration = ElementTree.SubElement(
        root,
        qti_tag("qti-response-declaration"),
        {
            "identifier": gap.response_identifier,
            "cardinality": "single",
            "base-type": "string",
        },
    )
    if not values:
        return False
    correct_response = ElementTree.SubElement(declaration, qti_tag("qti-correct-response"))
    if gap_points is None:
        # No mapping exists without own gap points, so every accepted value must
        # stand as its own correct response instead of dropping all but the first (D10).
        for value in values:
            value_element = ElementTree.SubElement(correct_response, qti_tag("qti-value"))
            value_element.text = value
        return False
    value_element = ElementTree.SubElement(correct_response, qti_tag("qti-value"))
    value_element.text = values[0]
    mapping = ElementTree.SubElement(
        declaration,
        qti_tag("qti-mapping"),
        {"default-value": "0", "lower-bound": "0", "upper-bound": gap_points},
    )
    for value in values:
        ElementTree.SubElement(
            mapping,
            qti_tag("qti-map-entry"),
            {"map-key": value, "mapped-value": gap_points, "case-sensitive": "false"},
        )
    return True


def gap_point_values(item: ExamNetQtiItem) -> tuple[str, ...] | None:
    """The formatted value every gap gets, or None when the writer maps no gap points.

    None means the item carries no total or no gaps, or a positive total's
    rounded-down share is 0.00. An explicit zero total maps every gap to zero;
    the checklist reads the same predicate so it does not report lost points.
    """

    if item.max_score is None or not item.response_gaps:
        return None
    value = (Decimal(str(item.max_score)) / len(item.response_gaps)).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )
    if value == 0 and item.max_score > 0:
        return None
    return (_format_points(value),) * len(item.response_gaps)


def _automatic_choice_value_count(item: ExamNetQtiItem) -> int:
    if item.evaluation_mode != ExamNetQtiEvaluationMode.AUTOMATIC or item.max_score is None:
        return 0
    if item.interaction_type in {
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    }:
        return len(item.correct_choice_identifiers)
    if item.interaction_type == ExamNetQtiInteractionType.MATCHING:
        return len(item.match_pairs)
    return 0


def _equal_choice_point_value(item: ExamNetQtiItem) -> str | None:
    count = _automatic_choice_value_count(item)
    if not count:
        return None
    total = Decimal(str(item.max_score))
    share = (total / count).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    if share * count != total:
        return None
    return _format_points(share)


def _format_points(value: Decimal) -> str:
    formatted = format(value, "f")
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def emits_map_response(item: ExamNetQtiItem) -> bool:
    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        return item.free_text_criterion_points is not None
    if item.interaction_type in (
        ExamNetQtiInteractionType.GAP_FILL,
        ExamNetQtiInteractionType.INLINE_CHOICE,
    ):
        return False
    return _equal_choice_point_value(item) is not None


def emits_all_or_nothing(item: ExamNetQtiItem) -> bool:
    """Use all-or-nothing only for keyed automatic choice or matching items."""

    return bool(_automatic_choice_value_count(item)) and _equal_choice_point_value(item) is None


def append_score_outcome(root: ElementTree.Element, item: ExamNetQtiItem) -> None:
    outcome = ElementTree.SubElement(
        root,
        qti_tag("qti-outcome-declaration"),
        {
            "identifier": "SCORE",
            "cardinality": "single",
            "base-type": "float",
        },
    )
    default_value = ElementTree.SubElement(outcome, qti_tag("qti-default-value"))
    value = ElementTree.SubElement(default_value, qti_tag("qti-value"))
    value.text = "0"
    max_score = ElementTree.SubElement(
        root,
        qti_tag("qti-outcome-declaration"),
        {
            "identifier": "MAXSCORE",
            "cardinality": "single",
            "base-type": "float",
        },
    )
    max_default = ElementTree.SubElement(max_score, qti_tag("qti-default-value"))
    max_value = ElementTree.SubElement(max_default, qti_tag("qti-value"))
    max_value.text = str(item.max_score or 0)


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
            qti_tag("qti-extended-text-interaction"),
            {
                "response-identifier": response_id,
                "expected-lines": "8",
            },
        )
        append_interaction_prompt(interaction, item, image_paths)
        return
    _append_match_interaction(parent, item, image_paths, response_id)


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
        qti_tag("qti-choice-interaction"),
        {
            "response-identifier": response_id,
            "max-choices": max_choices,
        },
    )
    append_interaction_prompt(interaction, item, image_paths)
    for choice in item.choices:
        _append_simple_choice(interaction, choice)


def _append_simple_choice(parent: ElementTree.Element, choice: ExamNetQtiChoice) -> None:
    choice_element = ElementTree.SubElement(
        parent,
        qti_tag("qti-simple-choice"),
        {"identifier": choice.identifier},
    )
    if choice.body:
        append_textual_paragraphs(choice_element, choice.body)
        return
    choice_element.text = choice.text


def _append_match_interaction(
    parent: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
    response_id: str,
) -> None:
    # Kategorisera grid (probe V51): rows are the first set, each row may match every
    # column; columns the second set, each column may match every row; each visible list
    # keeps its own order and the pairing lives only in the response data. The response
    # mapping is the shared equal-share/all-or-nothing path; a native grid's points equal
    # tick_points x pairs, so its exact share is exactly tick_points.
    row_count = len(item.match_left)
    column_count = len(item.match_right)
    interaction = ElementTree.SubElement(
        parent,
        qti_tag("qti-match-interaction"),
        {
            "response-identifier": response_id,
            "max-associations": str(row_count * column_count),
        },
    )
    append_interaction_prompt(interaction, item, image_paths)
    left_set = ElementTree.SubElement(interaction, qti_tag("qti-simple-match-set"))
    right_set = ElementTree.SubElement(interaction, qti_tag("qti-simple-match-set"))
    for entry in item.match_left:
        _append_associable_choice(left_set, entry, match_max=column_count)
    for entry in item.match_right:
        _append_associable_choice(right_set, entry, match_max=row_count)


def _append_associable_choice(
    parent: ElementTree.Element, entry: ExamNetQtiMatchEntry, *, match_max: int
) -> None:
    choice = ElementTree.SubElement(
        parent,
        qti_tag("qti-simple-associable-choice"),
        {"identifier": entry.identifier, "match-max": str(match_max)},
    )
    if entry.body:
        append_textual_paragraphs(choice, entry.body)
        return
    choice.text = entry.text
