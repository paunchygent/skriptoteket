"""QTI 3.0 qti-assessment-item serialization for Exam.net-oriented packages.

Purpose:
    Serialize one governed Exam.net QTI item to qti-assessment-item XML without file
    system or service-route concerns. A standalone item is one interaction; a
    parent item is the shared-instruction layout: the instruction at the top of
    the item body, then one interaction per child with its own response, and a
    SCORE that sums the children (the layout of the BF26 reference package).

Relationships:
    - Consumes `domain.examnet_qti_contracts` item value objects.
    - Builds elements with `domain.examnet_qti_xml`.
    - Used by QTI package planning before deterministic zip materialization and
      validation-report assembly.
"""

from __future__ import annotations

from dataclasses import replace
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_inline_prompt import (
    append_gap_fill_body,
    append_images,
    append_shared_instruction_body,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_rich_text import (
    MARK_ELEMENT_NAMES,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    QTI_NAMESPACE,
    QTI_SCHEMA_LOCATION,
    XSI_NAMESPACE,
    qti_tag,
    xsi_tag,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    MAP_RESPONSE_TEMPLATE,
    RESPONSE_IDENTIFIER,
    append_interaction,
    append_response_declaration,
    append_score_outcome,
    emits_all_or_nothing,
    emits_map_response,
)

_INLINE_TAGS: frozenset[str] = frozenset(
    {qti_tag(name) for name in MARK_ELEMENT_NAMES.values()}
    | {
        qti_tag("br"),
        qti_tag("img"),
        qti_tag("qti-text-entry-interaction"),
        qti_tag("qti-inline-choice-interaction"),
    }
)


def serialize_qti_assessment_item(
    item: ExamNetQtiItem,
    *,
    image_paths: tuple[str, ...] = (),
) -> bytes:
    """Serialize one governed QTI item to UTF-8 XML bytes."""

    ElementTree.register_namespace("", QTI_NAMESPACE)
    ElementTree.register_namespace("xsi", XSI_NAMESPACE)
    root = ElementTree.Element(
        qti_tag("qti-assessment-item"),
        {
            "identifier": item.item_id,
            "title": item.title,
            "adaptive": "false",
            "time-dependent": "false",
            xsi_tag("schemaLocation"): QTI_SCHEMA_LOCATION,
        },
    )
    if item.interaction_type is ExamNetQtiInteractionType.INFORMATION:
        _append_information_item(root, item, image_paths)
    elif item.children:
        _append_parent_item(root, item, image_paths)
    else:
        _append_standalone_item(root, item, image_paths)

    _indent_block_structure(root)
    xml_text = ElementTree.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8")


def _indent_block_structure(element: ElementTree.Element, level: int = 0) -> None:
    """Indent a block-only subtree and leave mixed inline content untouched.

    An element is block-only when it has children, its own text is ``None`` or
    empty, every child tail is ``None`` or empty, and no child is an inline
    element. A block-only element gets the same whitespace as
    ``ElementTree.indent(element, space="  ")`` at ``level``, so structure-only
    trees stay byte-identical. Any other element keeps its whole subtree exactly
    as built.
    """

    child_tags = [child.tag for child in element]
    if (
        not child_tags
        or element.text not in (None, "")
        or any(child.tail not in (None, "") for child in element)
        or any(tag in _INLINE_TAGS for tag in child_tags)
    ):
        return

    child_indentation = "\n" + "  " * (level + 1)
    element.text = child_indentation
    for index, child in enumerate(element):
        child.tail = "\n" + "  " * level if index == len(element) - 1 else child_indentation
    for child in element:
        _indent_block_structure(child, level + 1)


def _append_information_item(
    root: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    """Write an unnumbered information block: the prompt body and nothing else.

    Exam.net imports the item as an information block, so it carries no response
    declaration, no outcome declaration, no response processing and no rubric.
    """

    item_body = ElementTree.SubElement(root, qti_tag("qti-item-body"))
    append_shared_instruction_body(item_body, item, image_paths)


def _append_standalone_item(
    root: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    mapped_ids = append_response_declaration(root, item)
    append_score_outcome(root, item)
    item_body = ElementTree.SubElement(root, qti_tag("qti-item-body"))
    if item.interaction_type in (
        ExamNetQtiInteractionType.GAP_FILL,
        ExamNetQtiInteractionType.INLINE_CHOICE,
    ):
        append_gap_fill_body(item_body, item, image_paths)
        if not item.prompt_paragraphs:
            append_images(item_body, item.image_resources, image_paths)
    else:
        append_interaction(item_body, item, image_paths)
    if item.interaction_type is ExamNetQtiInteractionType.INLINE_CHOICE and mapped_ids:
        _append_score_sum(root, mapped_ids, ())
    elif emits_map_response(item):
        ElementTree.SubElement(
            root,
            qti_tag("qti-response-processing"),
            {"template": MAP_RESPONSE_TEMPLATE},
        )
    elif emits_all_or_nothing(item) and item.max_score is not None:
        _append_score_sum(root, (), ((RESPONSE_IDENTIFIER, item.max_score),))


def _append_parent_item(
    root: ElementTree.Element,
    parent: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    children = tuple(_qualified_child(child) for child in parent.children)
    stem_image_count = len(parent.image_resources) - sum(
        len(child.image_resources) for child in children
    )
    if stem_image_count < 0:
        raise ValueError("Parent image pool does not include its child resources.")
    child_image_paths = _split_image_paths(children, image_paths[stem_image_count:])
    mapped_response_ids: list[str] = []
    for child in children:
        if child.interaction_type in (
            ExamNetQtiInteractionType.GAP_FILL,
            ExamNetQtiInteractionType.INLINE_CHOICE,
        ):
            ElementTree.SubElement(
                root,
                qti_tag("qti-response-declaration"),
                {
                    "identifier": _separator_identifier(child),
                    "cardinality": "multiple",
                    "base-type": "directedPair",
                },
            )
        mapped_response_ids.extend(
            append_response_declaration(root, child, _response_identifier(child))
        )
    append_score_outcome(root, parent)
    item_body = ElementTree.SubElement(root, qti_tag("qti-item-body"))
    append_shared_instruction_body(item_body, parent, image_paths)
    for child, paths in zip(children, child_image_paths, strict=True):
        _append_child_body(item_body, child, paths)
    all_or_nothing_responses = tuple(
        (_response_identifier(child), child.max_score)
        for child in children
        if emits_all_or_nothing(child) and child.max_score is not None
    )
    if mapped_response_ids or all_or_nothing_responses:
        _append_score_sum(root, tuple(mapped_response_ids), all_or_nothing_responses)


def _append_child_body(
    item_body: ElementTree.Element,
    child: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    if child.interaction_type not in (
        ExamNetQtiInteractionType.GAP_FILL,
        ExamNetQtiInteractionType.INLINE_CHOICE,
    ):
        append_interaction(item_body, child, image_paths, _response_identifier(child))
        return
    # The empty gap-match starts the next sub-question in Exam.net; one before
    # every Lucktext child sentence keeps each sentence a sub-question of its own.
    ElementTree.SubElement(
        item_body,
        qti_tag("qti-gap-match-interaction"),
        {"response-identifier": _separator_identifier(child)},
    )
    append_gap_fill_body(item_body, child, image_paths)
    if not child.prompt_paragraphs:
        append_images(item_body, child.image_resources, image_paths)


def _append_score_sum(
    root: ElementTree.Element,
    response_ids: tuple[str, ...],
    all_or_nothing_responses: tuple[tuple[str, int | float], ...],
) -> None:
    processing = ElementTree.SubElement(root, qti_tag("qti-response-processing"))
    set_score = ElementTree.SubElement(
        processing, qti_tag("qti-set-outcome-value"), {"identifier": "SCORE"}
    )
    initial = ElementTree.SubElement(set_score, qti_tag("qti-base-value"), {"base-type": "float"})
    initial.text = "0"
    for response_id in response_ids:
        _append_mapped_score(processing, response_id)
    for response_id, points in all_or_nothing_responses:
        _append_all_or_nothing_score(processing, response_id, points)


def _append_mapped_score(processing: ElementTree.Element, response_id: str) -> None:
    condition = ElementTree.SubElement(processing, qti_tag("qti-response-condition"))
    response_if = ElementTree.SubElement(condition, qti_tag("qti-response-if"))
    # Avoid relying on an engine-specific map-response(NULL) result: NULL in a
    # sum would otherwise erase points already awarded to other children.
    not_null = ElementTree.SubElement(response_if, qti_tag("qti-not"))
    is_null = ElementTree.SubElement(not_null, qti_tag("qti-is-null"))
    ElementTree.SubElement(is_null, qti_tag("qti-variable"), {"identifier": response_id})
    total = _append_score_addition(response_if)
    ElementTree.SubElement(total, qti_tag("qti-map-response"), {"identifier": response_id})


def _append_all_or_nothing_score(
    processing: ElementTree.Element, response_id: str, max_score: int | float
) -> None:
    condition = ElementTree.SubElement(processing, qti_tag("qti-response-condition"))
    response_if = ElementTree.SubElement(condition, qti_tag("qti-response-if"))
    match = ElementTree.SubElement(response_if, qti_tag("qti-match"))
    ElementTree.SubElement(match, qti_tag("qti-variable"), {"identifier": response_id})
    ElementTree.SubElement(match, qti_tag("qti-correct"), {"identifier": response_id})
    total = _append_score_addition(response_if)
    points = ElementTree.SubElement(total, qti_tag("qti-base-value"), {"base-type": "float"})
    points.text = str(max_score)


def _append_score_addition(response_if: ElementTree.Element) -> ElementTree.Element:
    set_score = ElementTree.SubElement(
        response_if, qti_tag("qti-set-outcome-value"), {"identifier": "SCORE"}
    )
    total = ElementTree.SubElement(set_score, qti_tag("qti-sum"))
    ElementTree.SubElement(total, qti_tag("qti-variable"), {"identifier": "SCORE"})
    return total


def _qualified_child(child: ExamNetQtiItem) -> ExamNetQtiItem:
    """Prefix the child's gap responses with its id so they stay unique inside the parent."""

    return replace(
        child,
        text_entry_gaps=tuple(
            replace(gap, response_identifier=f"{child.item_id}_{gap.response_identifier}")
            for gap in child.text_entry_gaps
        ),
        inline_choice_gaps=tuple(
            replace(gap, response_identifier=f"{child.item_id}_{gap.response_identifier}")
            for gap in child.inline_choice_gaps
        ),
    )


def _response_identifier(child: ExamNetQtiItem) -> str:
    return f"{child.item_id}_RESPONSE"


def _separator_identifier(child: ExamNetQtiItem) -> str:
    return f"{child.item_id}_SEPARATOR"


def _split_image_paths(
    children: tuple[ExamNetQtiItem, ...],
    image_paths: tuple[str, ...],
) -> tuple[tuple[str, ...], ...]:
    """Hand each child the next slice of the parent's image paths, in child order."""

    slices: list[tuple[str, ...]] = []
    start = 0
    for child in children:
        end = start + len(child.image_resources)
        slices.append(image_paths[start:end])
        start = end
    if start != len(image_paths):
        raise ValueError("Parent image paths must match its children's image resources.")
    return tuple(slices)
