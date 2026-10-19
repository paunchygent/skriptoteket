"""Shared-instruction parent layout reader for Exam.net QTI items.

Responsibility: split a parent item body into supported block and gap children
plus one skipped entry per unsupported child.
"""

from __future__ import annotations

from collections.abc import Mapping
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_block_item_reader import (
    choice_item,
    free_text_item,
    matching_item,
    ordering_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    ExamNetQtiUnsupportedContent,
    read_rich_content,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_gap_item_reader import (
    gap_fill_item,
    inline_choice_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiReadItem,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_scores import (
    ResponseDeclaration,
    apply_unknown_remainder,
    block_child_points,
    gap_child_points,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    BLOCK_INTERACTIONS,
    GAP_INTERACTIONS,
    OPENING_TEXT_LIMIT,
    SEPARATOR,
    UnsupportedImage,
    UnsupportedInteraction,
    image_resources,
    local_name,
    prompt_lines,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)


def read_parent_layout(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    declarations: Mapping[str, ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> tuple[ExamNetQtiReadItem, ...]:
    """Read the shared-instruction layout: one item plus one entry per skipped child.

    The instruction is the content before the first interaction or separator. A
    block interaction is one child read from its own prompt; a separator opens a
    gap child whose body runs to the next child. Content after a block child is
    carried into the next child's prompt, or the last child's prompt when none.
    """

    nodes = list(body)
    start_positions = [index for index, element in enumerate(nodes) if is_child_start(element)]
    identifier = root.get("identifier") or ""

    instruction_body = read_rich_content(nodes[: start_positions[0]], leading_text=body.text)
    if instruction_body.gap_elements:
        raise UnsupportedInteraction
    instruction_images = image_resources(
        instruction_body.image_elements, item_path=item_path, files=files
    )

    children: list[ExamNetQtiItem] = []
    unsupported: list[ExamNetQtiUnsupportedItem] = []
    carry: tuple[ElementTree.Element, ...] = ()
    for position, start in enumerate(start_positions):
        end = start_positions[position + 1] if position + 1 < len(start_positions) else len(nodes)
        element = nodes[start]
        trailing = tuple(nodes[start + 1 : end])
        is_last = position == len(start_positions) - 1
        is_separator = element.tag == SEPARATOR and len(element) == 0
        try:
            if is_separator:
                child = _read_gap_child(
                    element,
                    body_nodes=(*carry, *trailing),
                    identifier=identifier,
                    child_number=position + 1,
                    declarations=declarations,
                    item_path=item_path,
                    files=files,
                )
            elif element.tag in BLOCK_INTERACTIONS:
                child = _read_block_child(
                    root,
                    block=element,
                    carry=carry,
                    trailing=trailing,
                    is_last=is_last,
                    identifier=identifier,
                    child_number=position + 1,
                    declarations=declarations,
                    item_path=item_path,
                    files=files,
                )
            else:
                raise UnsupportedInteraction
        except UnsupportedImage:
            unsupported.append(
                _unsupported_child(element, trailing, sequence, ExamNetQtiUnsupportedReason.IMAGE)
            )
            carry = () if (is_separator or is_last) else trailing
            continue
        except (ExamNetQtiUnsupportedContent, UnsupportedInteraction):
            unsupported.append(
                _unsupported_child(
                    element, trailing, sequence, ExamNetQtiUnsupportedReason.INTERACTION
                )
            )
            carry = () if (is_separator or is_last) else trailing
            continue
        children.append(child)
        carry = () if (is_separator or is_last) else trailing

    apply_unknown_remainder(children, max_score)
    if not children:
        return tuple(unsupported)

    first = children[0]
    instruction_lines = prompt_lines(instruction_body.paragraphs)
    parent = ExamNetQtiItem(
        item_id=identifier,
        sequence=sequence,
        title=root.get("title") or "",
        interaction_type=first.interaction_type,
        prompt_lines=instruction_lines,
        max_score=max_score,
        prompt_paragraphs=instruction_body.paragraphs,
        evaluation_mode=(
            ExamNetQtiEvaluationMode.MANUAL_UNKEYED
            if any(
                child.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
                for child in children
            )
            else ExamNetQtiEvaluationMode.AUTOMATIC
        ),
        image_resources=(
            *instruction_images,
            *(image for child in children for image in child.image_resources),
        ),
        instruction_lines=instruction_lines,
        children=tuple(children),
    )
    return (parent, *unsupported)


def _read_block_child(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    carry: tuple[ElementTree.Element, ...],
    trailing: tuple[ElementTree.Element, ...],
    is_last: bool,
    identifier: str,
    child_number: int,
    declarations: Mapping[str, ResponseDeclaration],
    item_path: str,
    files: Mapping[str, bytes],
) -> ExamNetQtiItem:
    lead = read_rich_content(carry, leading_text=None)
    prompt_element = block.find(qti_tag("qti-prompt"))
    if prompt_element is None:
        prompt = read_rich_content(())
    else:
        prompt = read_rich_content(
            list(prompt_element),
            leading_text=prompt_element.text,
            image_offset=len(lead.image_elements),
            gap_offset=len(lead.gap_elements),
        )
    if is_last:
        after = read_rich_content(
            trailing,
            leading_text=block.tail,
            image_offset=len(lead.image_elements) + len(prompt.image_elements),
            gap_offset=len(lead.gap_elements) + len(prompt.gap_elements),
        )
    else:
        after = read_rich_content(())
    if lead.gap_elements or prompt.gap_elements or after.gap_elements:
        raise UnsupportedInteraction

    prompt_paragraphs = (*lead.paragraphs, *prompt.paragraphs, *after.paragraphs)
    resolved_images = image_resources(
        (*lead.image_elements, *prompt.image_elements, *after.image_elements),
        item_path=item_path,
        files=files,
    )
    response_identifier = block.get("response-identifier")
    declaration = declarations.get(response_identifier) if response_identifier else None
    if response_identifier is None or declaration is None:
        raise UnsupportedInteraction

    child_root = _child_root(identifier, child_number)
    child_max_score = block_child_points(root, response_identifier, declaration)
    if block.tag == qti_tag("qti-choice-interaction"):
        return choice_item(
            child_root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=resolved_images,
            max_score=child_max_score,
            sequence=child_number,
        )
    if block.tag == qti_tag("qti-order-interaction"):
        return ordering_item(
            child_root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=resolved_images,
            max_score=child_max_score,
            sequence=child_number,
        )
    if block.tag == qti_tag("qti-match-interaction"):
        return matching_item(
            child_root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=resolved_images,
            max_score=child_max_score,
            sequence=child_number,
        )
    return free_text_item(
        child_root,
        declaration=declaration,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=resolved_images,
        max_score=child_max_score,
        sequence=child_number,
    )


def _read_gap_child(
    separator: ElementTree.Element,
    *,
    body_nodes: tuple[ElementTree.Element, ...],
    identifier: str,
    child_number: int,
    declarations: Mapping[str, ResponseDeclaration],
    item_path: str,
    files: Mapping[str, bytes],
) -> ExamNetQtiItem:
    read_body = read_rich_content(body_nodes, leading_text=separator.tail)
    if not read_body.gap_elements:
        raise UnsupportedInteraction
    gap_names = {local_name(element.tag) for element in read_body.gap_elements}
    if gap_names not in (
        {"qti-text-entry-interaction"},
        {"qti-inline-choice-interaction"},
    ):
        raise UnsupportedInteraction

    child_root = _child_root(identifier, child_number)
    child_max_score = gap_child_points(declarations, read_body.gap_elements)
    if gap_names == {"qti-text-entry-interaction"}:
        return gap_fill_item(
            child_root,
            read_body=read_body,
            declarations=declarations,
            max_score=child_max_score,
            item_path=item_path,
            files=files,
            sequence=child_number,
        )
    return inline_choice_item(
        child_root,
        read_body=read_body,
        declarations=declarations,
        max_score=child_max_score,
        item_path=item_path,
        files=files,
        sequence=child_number,
    )


def _child_root(identifier: str, child_number: int) -> ElementTree.Element:
    return ElementTree.Element(
        qti_tag("qti-assessment-item"),
        {"identifier": f"{identifier}_child_{child_number}"},
    )


def is_child_start(element: ElementTree.Element) -> bool:
    tag = element.tag
    if not isinstance(tag, str) or tag in GAP_INTERACTIONS:
        return False
    return tag.rsplit("}", 1)[-1].endswith("-interaction")


def _unsupported_child(
    element: ElementTree.Element,
    trailing: tuple[ElementTree.Element, ...],
    sequence: int,
    reason: ExamNetQtiUnsupportedReason,
) -> ExamNetQtiUnsupportedItem:
    is_separator = element.tag == SEPARATOR and len(element) == 0
    nodes = (element, *trailing) if is_separator else (element,)
    text = " ".join("".join(node.itertext()) for node in nodes)
    return ExamNetQtiUnsupportedItem(
        sequence=sequence,
        opening_text=" ".join(text.split())[:OPENING_TEXT_LIMIT],
        reason=reason,
    )
