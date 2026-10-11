"""QTI 2.1 assessmentItem serialization for Exam.net-oriented packages.

Purpose:
    Serialize one governed Exam.net QTI item to assessmentItem XML without file
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
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    MAP_RESPONSE_TEMPLATE,
    QTI_NAMESPACE,
    QTI_SCHEMA_LOCATION,
    XSI_NAMESPACE,
    append_gap_fill_body,
    append_images,
    append_interaction,
    append_response_declaration,
    append_score_outcome,
    emits_map_response,
    normalized_prompt_lines,
    qti_tag,
    xsi_tag,
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
        qti_tag("assessmentItem"),
        {
            "identifier": item.item_id,
            "title": item.title,
            "adaptive": "false",
            "timeDependent": "false",
            xsi_tag("schemaLocation"): QTI_SCHEMA_LOCATION,
        },
    )
    if item.children:
        _append_parent_item(root, item, image_paths)
    else:
        _append_standalone_item(root, item, image_paths)

    ElementTree.indent(root, space="  ")
    xml_text = ElementTree.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8")


def _append_standalone_item(
    root: ElementTree.Element,
    item: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    append_response_declaration(root, item)
    append_score_outcome(root, item)
    item_body = ElementTree.SubElement(root, qti_tag("itemBody"))
    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        append_gap_fill_body(item_body, item)
        append_images(item_body, item.image_resources, image_paths)
    else:
        append_interaction(item_body, item, image_paths)
    if emits_map_response(item):
        ElementTree.SubElement(
            root,
            qti_tag("responseProcessing"),
            {"template": MAP_RESPONSE_TEMPLATE},
        )


def _append_parent_item(
    root: ElementTree.Element,
    parent: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    children = tuple(_qualified_child(child) for child in parent.children)
    child_image_paths = _split_image_paths(children, image_paths)
    mapped_response_ids: list[str] = []
    for child in children:
        if child.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
            ElementTree.SubElement(
                root,
                qti_tag("responseDeclaration"),
                {
                    "identifier": _separator_identifier(child),
                    "cardinality": "multiple",
                    "baseType": "directedPair",
                },
            )
        mapped_response_ids.extend(
            append_response_declaration(root, child, _response_identifier(child))
        )
    append_score_outcome(root, parent)
    item_body = ElementTree.SubElement(root, qti_tag("itemBody"))
    for line in normalized_prompt_lines(parent.instruction_lines):
        ElementTree.SubElement(item_body, qti_tag("p")).text = line
    for child, paths in zip(children, child_image_paths, strict=True):
        _append_child_body(item_body, child, paths)
    if mapped_response_ids:
        _append_score_sum(root, tuple(mapped_response_ids))


def _append_child_body(
    item_body: ElementTree.Element,
    child: ExamNetQtiItem,
    image_paths: tuple[str, ...],
) -> None:
    if child.interaction_type != ExamNetQtiInteractionType.GAP_FILL:
        append_interaction(item_body, child, image_paths, _response_identifier(child))
        return
    # The empty gap-match starts the next sub-question in Exam.net; one before
    # every Lucktext child sentence keeps each sentence a sub-question of its own.
    ElementTree.SubElement(
        item_body,
        qti_tag("gapMatchInteraction"),
        {"responseIdentifier": _separator_identifier(child)},
    )
    append_gap_fill_body(item_body, child)
    append_images(item_body, child.image_resources, image_paths)


def _append_score_sum(root: ElementTree.Element, response_ids: tuple[str, ...]) -> None:
    processing = ElementTree.SubElement(root, qti_tag("responseProcessing"))
    set_score = ElementTree.SubElement(
        processing, qti_tag("setOutcomeValue"), {"identifier": "SCORE"}
    )
    total = ElementTree.SubElement(set_score, qti_tag("sum"))
    for response_id in response_ids:
        ElementTree.SubElement(total, qti_tag("mapResponse"), {"identifier": response_id})


def _qualified_child(child: ExamNetQtiItem) -> ExamNetQtiItem:
    """Prefix the child's gap responses with its id so they stay unique inside the parent."""

    return replace(
        child,
        text_entry_gaps=tuple(
            replace(gap, response_identifier=f"{child.item_id}_{gap.response_identifier}")
            for gap in child.text_entry_gaps
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
