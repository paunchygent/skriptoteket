"""Read one QTI 3.0 assessment item back into the export's item value object.

Purpose:
    Invert ``examnet_qti_item_xml.serialize_qti_assessment_item`` for standalone
    items: response declarations, ``MAXSCORE``, prompt content, interactions,
    choices, gaps, matching lists and image resources become the
    ``ExamNetQtiItem`` the export started from, up to HTML whitespace
    normalization. Items whose layout the current import does not map become an
    ``ExamNetQtiUnsupportedItem`` with a reason the mapper turns into a visible
    note. Unsafe XML and unsupported QTI versions refuse the whole package
    instead.

Relationships:
    - Consumes the read-side contracts of ``examnet_qti_import_contracts``.
    - Uses ``examnet_qti_body_reader`` for prompt paragraphs, choices and gaps.
    - Consumed by ``exam_workspace.qti_import``; a parent item reads back as one
      item with its supported children and one skipped entry per unsupported child.
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    ExamNetQtiReadBody,
    ExamNetQtiUnsupportedContent,
    paragraphs_plain_text,
    read_rich_content,
    read_text_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiPromptParagraph,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageSource,
    ExamNetQtiReadItem,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)
from skriptoteket.domain.errors import validation_error

__all__ = [
    "read_examnet_qti_item",
    "read_examnet_qti_items",
]

_BLOCK_INTERACTIONS = frozenset(
    {
        qti_tag("qti-choice-interaction"),
        qti_tag("qti-order-interaction"),
        qti_tag("qti-match-interaction"),
        qti_tag("qti-extended-text-interaction"),
    }
)
_SEPARATOR = qti_tag("qti-gap-match-interaction")
_GAP_INTERACTIONS = frozenset(
    {
        qti_tag("qti-text-entry-interaction"),
        qti_tag("qti-inline-choice-interaction"),
    }
)
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_OPENING_TEXT_LIMIT = 200
_UNSAFE_XML = "QTI-paketet innehåller en otillåten XML-konstruktion."
_INVALID_ITEM_XML = "QTI-paketet innehåller en fråga som inte är giltig XML."
_UNSUPPORTED_VERSION = (
    "QTI-paketet använder en QTI-version som inte stöds. Endast QTI 3.0 kan importeras."
)


class _UnsupportedInteraction(Exception):
    """Raised when the item's structure is outside the supported standalone shapes."""


class _UnsupportedImage(Exception):
    """Raised when one image cannot be resolved to a supported package payload."""


@dataclass(frozen=True)
class _MappingEntry:
    map_key: str
    mapped_value: str


@dataclass(frozen=True)
class _Mapping:
    upper_bound: str | None
    entries: tuple[_MappingEntry, ...]


@dataclass(frozen=True)
class _ResponseDeclaration:
    cardinality: str
    base_type: str
    correct_values: tuple[str, ...]
    mapping: _Mapping | None


def read_examnet_qti_items(
    source: ExamNetQtiPackageSource,
) -> tuple[ExamNetQtiReadItem, ...]:
    """Read every item XML file the package names, in test order."""

    read_items: list[ExamNetQtiReadItem] = []
    for sequence, item_source in enumerate(source.items, start=1):
        read_items.extend(
            read_examnet_qti_item(
                xml=item_source.xml,
                item_path=item_source.path,
                files=source.files,
                sequence=sequence,
            )
        )
    return tuple(read_items)


def read_examnet_qti_item(
    *,
    xml: bytes,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> tuple[ExamNetQtiReadItem, ...]:
    """Read one item; a parent layout returns the item plus one entry per skipped child."""

    root = _parse_item(xml, item_path=item_path)
    try:
        return _read_item(
            root,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    except _UnsupportedImage:
        return (_unsupported_item(root, sequence, ExamNetQtiUnsupportedReason.IMAGE),)
    except (ExamNetQtiUnsupportedContent, _UnsupportedInteraction):
        return (_unsupported_item(root, sequence, ExamNetQtiUnsupportedReason.INTERACTION),)


def _parse_item(xml: bytes, *, item_path: str) -> ElementTree.Element:
    if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
        raise validation_error(_UNSAFE_XML, {"path": item_path})
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise validation_error(_INVALID_ITEM_XML, {"path": item_path}) from error
    if root.tag != qti_tag("qti-assessment-item"):
        raise validation_error(_UNSUPPORTED_VERSION, {"path": item_path})
    return root


def _read_item(
    root: ElementTree.Element,
    *,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> tuple[ExamNetQtiReadItem, ...]:
    body = root.find(qti_tag("qti-item-body"))
    if body is None:
        raise _UnsupportedInteraction

    body_children = list(body)
    blocks = [element for element in body_children if element.tag in _BLOCK_INTERACTIONS]
    starts = [element for element in body_children if _is_child_start(element)]
    declarations = _response_declarations(root)
    max_score = _max_score(root)

    if len(blocks) == 1 and len(starts) == 1:
        return (
            _read_block_item(
                root,
                body=body,
                block=blocks[0],
                declarations=declarations,
                max_score=max_score,
                item_path=item_path,
                files=files,
                sequence=sequence,
            ),
        )
    if not starts:
        return (
            _read_gap_item(
                root,
                body=body,
                declarations=declarations,
                max_score=max_score,
                item_path=item_path,
                files=files,
                sequence=sequence,
            ),
        )
    return _read_parent_layout(
        root,
        body=body,
        declarations=declarations,
        max_score=max_score,
        item_path=item_path,
        files=files,
        sequence=sequence,
    )


def _read_parent_layout(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    declarations: Mapping[str, _ResponseDeclaration],
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
    start_positions = [index for index, element in enumerate(nodes) if _is_child_start(element)]
    identifier = root.get("identifier") or ""

    instruction_body = read_rich_content(nodes[: start_positions[0]], leading_text=body.text)
    if instruction_body.gap_elements:
        raise _UnsupportedInteraction
    instruction_images = _image_resources(
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
        is_separator = element.tag == _SEPARATOR and len(element) == 0
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
            elif element.tag in _BLOCK_INTERACTIONS:
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
                raise _UnsupportedInteraction
        except _UnsupportedImage:
            unsupported.append(
                _unsupported_child(element, trailing, sequence, ExamNetQtiUnsupportedReason.IMAGE)
            )
            carry = () if (is_separator or is_last) else trailing
            continue
        except (ExamNetQtiUnsupportedContent, _UnsupportedInteraction):
            unsupported.append(
                _unsupported_child(
                    element, trailing, sequence, ExamNetQtiUnsupportedReason.INTERACTION
                )
            )
            carry = () if (is_separator or is_last) else trailing
            continue
        children.append(child)
        carry = () if (is_separator or is_last) else trailing

    _apply_unknown_remainder(children, max_score)
    if not children:
        return tuple(unsupported)

    first = children[0]
    instruction_lines = _prompt_lines(instruction_body.paragraphs)
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
    declarations: Mapping[str, _ResponseDeclaration],
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
        raise _UnsupportedInteraction

    prompt_paragraphs = (*lead.paragraphs, *prompt.paragraphs, *after.paragraphs)
    image_resources = _image_resources(
        (*lead.image_elements, *prompt.image_elements, *after.image_elements),
        item_path=item_path,
        files=files,
    )
    response_identifier = block.get("response-identifier")
    declaration = declarations.get(response_identifier) if response_identifier else None
    if response_identifier is None or declaration is None:
        raise _UnsupportedInteraction

    child_root = _child_root(identifier, child_number)
    child_max_score = _block_child_points(root, response_identifier, declaration)
    if block.tag == qti_tag("qti-choice-interaction"):
        return _choice_item(
            child_root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=child_max_score,
            sequence=child_number,
        )
    if block.tag == qti_tag("qti-order-interaction"):
        return _ordering_item(
            child_root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=child_max_score,
            sequence=child_number,
        )
    if block.tag == qti_tag("qti-match-interaction"):
        return _matching_item(
            child_root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=child_max_score,
            sequence=child_number,
        )
    return _free_text_item(
        child_root,
        declaration=declaration,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=child_max_score,
        sequence=child_number,
    )


def _read_gap_child(
    separator: ElementTree.Element,
    *,
    body_nodes: tuple[ElementTree.Element, ...],
    identifier: str,
    child_number: int,
    declarations: Mapping[str, _ResponseDeclaration],
    item_path: str,
    files: Mapping[str, bytes],
) -> ExamNetQtiItem:
    read_body = read_rich_content(body_nodes, leading_text=separator.tail)
    if not read_body.gap_elements:
        raise _UnsupportedInteraction
    gap_names = {_local_name(element.tag) for element in read_body.gap_elements}
    if gap_names not in (
        {"qti-text-entry-interaction"},
        {"qti-inline-choice-interaction"},
    ):
        raise _UnsupportedInteraction

    child_root = _child_root(identifier, child_number)
    child_max_score = _gap_child_points(declarations, read_body.gap_elements)
    if gap_names == {"qti-text-entry-interaction"}:
        return _gap_fill_item(
            child_root,
            read_body=read_body,
            declarations=declarations,
            max_score=child_max_score,
            item_path=item_path,
            files=files,
            sequence=child_number,
        )
    return _inline_choice_item(
        child_root,
        read_body=read_body,
        declarations=declarations,
        max_score=child_max_score,
        item_path=item_path,
        files=files,
        sequence=child_number,
    )


def _block_child_points(
    root: ElementTree.Element,
    response_identifier: str,
    declaration: _ResponseDeclaration,
) -> int | float | None:
    if declaration.mapping is not None and declaration.mapping.upper_bound is not None:
        return _number(declaration.mapping.upper_bound)
    return _all_or_nothing_points(root, response_identifier)


def _all_or_nothing_points(
    root: ElementTree.Element,
    response_identifier: str,
) -> int | float | None:
    processing = root.find(qti_tag("qti-response-processing"))
    if processing is None:
        return None
    for condition in processing.findall(qti_tag("qti-response-condition")):
        response_if = condition.find(qti_tag("qti-response-if"))
        if response_if is None:
            continue
        match = response_if.find(qti_tag("qti-match"))
        if match is None:
            continue
        variable = match.find(qti_tag("qti-variable"))
        correct = match.find(qti_tag("qti-correct"))
        if variable is None or correct is None:
            continue
        if (
            variable.get("identifier") != response_identifier
            or correct.get("identifier") != response_identifier
        ):
            continue
        set_outcome = response_if.find(qti_tag("qti-set-outcome-value"))
        if set_outcome is None:
            return None
        total = set_outcome.find(qti_tag("qti-sum"))
        if total is None:
            return None
        points = total.find(qti_tag("qti-base-value"))
        if points is None or points.text is None:
            return None
        return _number(points.text)
    return None


def _gap_child_points(
    declarations: Mapping[str, _ResponseDeclaration],
    gap_elements: tuple[ElementTree.Element, ...],
) -> int | float | None:
    values: set[Decimal] = set()
    for element in gap_elements:
        response_identifier = element.get("response-identifier")
        declaration = declarations.get(response_identifier) if response_identifier else None
        if declaration is None or declaration.mapping is None or not declaration.mapping.entries:
            return None
        for entry in declaration.mapping.entries:
            values.add(_decimal(entry.mapped_value))
    if len(values) != 1:
        return None
    return _recover_total(len(gap_elements), next(iter(values)))


def _recover_total(gap_count: int, gap_value: Decimal) -> int | float:
    """The export's total from its rounded-down per-gap share (see gap_point_values)."""

    lower = gap_count * gap_value
    upper = lower + gap_count * Decimal("0.01")
    smallest_integer = lower.to_integral_value(rounding=ROUND_CEILING)
    if smallest_integer < upper:
        return _to_number(smallest_integer)
    smallest_tenth = (lower * 10).to_integral_value(rounding=ROUND_CEILING) / Decimal(10)
    if smallest_tenth < upper:
        return _to_number(smallest_tenth)
    return _to_number(lower)


def _apply_unknown_remainder(
    children: list[ExamNetQtiItem],
    max_score: int | float | None,
) -> None:
    """Give a single child without its own points the parent total's remainder."""

    if max_score is None:
        return
    unknown = [index for index, child in enumerate(children) if child.max_score is None]
    if len(unknown) != 1:
        return
    known = sum(
        (Decimal(str(child.max_score)) for child in children if child.max_score is not None),
        Decimal(0),
    )
    remainder = Decimal(str(max_score)) - known
    if remainder <= 0:
        return
    position = unknown[0]
    children[position] = replace(children[position], max_score=_to_number(remainder))


def _child_root(identifier: str, child_number: int) -> ElementTree.Element:
    return ElementTree.Element(
        qti_tag("qti-assessment-item"),
        {"identifier": f"{identifier}_child_{child_number}"},
    )


def _is_child_start(element: ElementTree.Element) -> bool:
    tag = element.tag
    if not isinstance(tag, str) or tag in _GAP_INTERACTIONS:
        return False
    return tag.rsplit("}", 1)[-1].endswith("-interaction")


def _unsupported_child(
    element: ElementTree.Element,
    trailing: tuple[ElementTree.Element, ...],
    sequence: int,
    reason: ExamNetQtiUnsupportedReason,
) -> ExamNetQtiUnsupportedItem:
    is_separator = element.tag == _SEPARATOR and len(element) == 0
    nodes = (element, *trailing) if is_separator else (element,)
    text = " ".join("".join(node.itertext()) for node in nodes)
    return ExamNetQtiUnsupportedItem(
        sequence=sequence,
        opening_text=" ".join(text.split())[:_OPENING_TEXT_LIMIT],
        reason=reason,
    )


def _read_block_item(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    block: ElementTree.Element,
    declarations: Mapping[str, _ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    before, prompt, after = _read_block_prompt(
        body=body,
        block=block,
    )
    if before.gap_elements or prompt.gap_elements or after.gap_elements:
        raise _UnsupportedInteraction

    prompt_paragraphs = (*before.paragraphs, *prompt.paragraphs, *after.paragraphs)
    image_elements = (
        *before.image_elements,
        *prompt.image_elements,
        *after.image_elements,
    )
    image_resources = _image_resources(image_elements, item_path=item_path, files=files)
    response_identifier = block.get("response-identifier")
    declaration = declarations.get(response_identifier) if response_identifier else None
    if declaration is None:
        raise _UnsupportedInteraction

    if block.tag == qti_tag("qti-choice-interaction"):
        return _choice_item(
            root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=max_score,
            sequence=sequence,
        )
    if block.tag == qti_tag("qti-order-interaction"):
        return _ordering_item(
            root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=max_score,
            sequence=sequence,
        )
    if block.tag == qti_tag("qti-match-interaction"):
        return _matching_item(
            root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=max_score,
            sequence=sequence,
        )
    return _free_text_item(
        root,
        declaration=declaration,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        sequence=sequence,
    )


def _read_block_prompt(
    *,
    body: ElementTree.Element,
    block: ElementTree.Element,
) -> tuple[ExamNetQtiReadBody, ExamNetQtiReadBody, ExamNetQtiReadBody]:
    children = list(body)
    position = children.index(block)
    before = read_rich_content(children[:position], leading_text=body.text)

    prompt_element = block.find(qti_tag("qti-prompt"))
    if prompt_element is None:
        prompt = read_rich_content(())
    else:
        prompt = read_rich_content(
            list(prompt_element),
            leading_text=prompt_element.text,
            image_offset=len(before.image_elements),
            gap_offset=len(before.gap_elements),
        )

    after = read_rich_content(
        children[position + 1 :],
        leading_text=block.tail,
        image_offset=len(before.image_elements) + len(prompt.image_elements),
        gap_offset=len(before.gap_elements) + len(prompt.gap_elements),
    )
    return before, prompt, after


def _choice_item(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    declaration: _ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    if declaration.cardinality == "single":
        interaction_type = ExamNetQtiInteractionType.SINGLE_CHOICE
    elif declaration.cardinality == "multiple":
        interaction_type = ExamNetQtiInteractionType.MULTIPLE_RESPONSE
    else:
        raise _UnsupportedInteraction
    return _item(
        root,
        sequence=sequence,
        interaction_type=interaction_type,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        choices=tuple(_choice(element) for element in block.findall(qti_tag("qti-simple-choice"))),
        correct_choice_identifiers=declaration.correct_values,
    )


def _ordering_item(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    declaration: _ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    return _item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.ORDERING,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        choices=tuple(_choice(element) for element in block.findall(qti_tag("qti-simple-choice"))),
        correct_choice_identifiers=declaration.correct_values,
    )


def _matching_item(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    declaration: _ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    match_sets = block.findall(qti_tag("qti-simple-match-set"))
    if len(match_sets) != 2:
        raise _UnsupportedInteraction
    match_left = tuple(
        _match_entry(element)
        for element in match_sets[0].findall(qti_tag("qti-simple-associable-choice"))
    )
    match_right = tuple(
        _match_entry(element)
        for element in match_sets[1].findall(qti_tag("qti-simple-associable-choice"))
    )
    left_by_identifier = {entry.identifier: entry for entry in match_left}
    right_by_identifier = {entry.identifier: entry for entry in match_right}
    pairs: list[ExamNetQtiMatchPair] = []
    for value in declaration.correct_values:
        identifiers = value.split()
        if len(identifiers) != 2:
            raise _UnsupportedInteraction
        left_identifier, right_identifier = identifiers
        left = left_by_identifier.get(left_identifier)
        right = right_by_identifier.get(right_identifier)
        if left is None or right is None:
            raise _UnsupportedInteraction
        pairs.append(
            ExamNetQtiMatchPair(
                left_identifier=left.identifier,
                left_text=left.text,
                right_identifier=right.identifier,
                right_text=right.text,
            )
        )
    return _item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.MATCHING,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        match_left=match_left,
        match_right=match_right,
        match_pairs=tuple(pairs),
    )


def _free_text_item(
    root: ElementTree.Element,
    *,
    declaration: _ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    if declaration.mapping is None:
        return _item(
            root,
            sequence=sequence,
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=max_score,
            evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED,
            free_text_criterion_points=None,
        )
    if not declaration.mapping.entries:
        raise _UnsupportedInteraction
    return _item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        free_text_criterion_points=_number(declaration.mapping.entries[0].mapped_value),
    )


def _read_gap_item(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    declarations: Mapping[str, _ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    read_body = read_rich_content(list(body), leading_text=body.text)
    if not read_body.gap_elements:
        raise _UnsupportedInteraction
    gap_names = {_local_name(element.tag) for element in read_body.gap_elements}
    if gap_names == {"qti-text-entry-interaction"}:
        return _gap_fill_item(
            root,
            read_body=read_body,
            declarations=declarations,
            max_score=max_score,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    if gap_names == {"qti-inline-choice-interaction"}:
        return _inline_choice_item(
            root,
            read_body=read_body,
            declarations=declarations,
            max_score=max_score,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    raise _UnsupportedInteraction


def _gap_fill_item(
    root: ElementTree.Element,
    *,
    read_body: ExamNetQtiReadBody,
    declarations: Mapping[str, _ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    return _item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_paragraphs=read_body.paragraphs,
        image_resources=_image_resources(
            read_body.image_elements, item_path=item_path, files=files
        ),
        max_score=max_score,
        text_entry_gaps=tuple(
            _text_entry_gap(element, declarations) for element in read_body.gap_elements
        ),
    )


def _inline_choice_item(
    root: ElementTree.Element,
    *,
    read_body: ExamNetQtiReadBody,
    declarations: Mapping[str, _ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    return _item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.INLINE_CHOICE,
        prompt_paragraphs=read_body.paragraphs,
        image_resources=_image_resources(
            read_body.image_elements, item_path=item_path, files=files
        ),
        max_score=max_score,
        inline_choice_gaps=tuple(
            _inline_choice_gap(element, declarations) for element in read_body.gap_elements
        ),
    )


def _text_entry_gap(
    element: ElementTree.Element,
    declarations: Mapping[str, _ResponseDeclaration],
) -> ExamNetQtiTextEntryGap:
    response_identifier, declaration = _bound_declaration(element, declarations)
    accepted_values: list[str] = []
    for value in declaration.correct_values:
        stripped = value.strip()
        if stripped:
            accepted_values.append(stripped)
    if declaration.mapping is not None:
        for entry in declaration.mapping.entries:
            stripped = entry.map_key.strip()
            if stripped and stripped not in accepted_values:
                accepted_values.append(stripped)
    return ExamNetQtiTextEntryGap(
        response_identifier=response_identifier,
        label="",
        accepted_values=tuple(accepted_values),
    )


def _inline_choice_gap(
    element: ElementTree.Element,
    declarations: Mapping[str, _ResponseDeclaration],
) -> ExamNetQtiInlineChoiceGap:
    response_identifier, declaration = _bound_declaration(element, declarations)
    if len(declaration.correct_values) != 1:
        raise _UnsupportedInteraction
    options = tuple(_choice(option) for option in element.findall(qti_tag("qti-inline-choice")))
    correct_option_identifier = declaration.correct_values[0]
    if correct_option_identifier not in {option.identifier for option in options}:
        raise _UnsupportedInteraction
    return ExamNetQtiInlineChoiceGap(
        response_identifier=response_identifier,
        options=options,
        correct_option_identifier=correct_option_identifier,
    )


def _bound_declaration(
    element: ElementTree.Element,
    declarations: Mapping[str, _ResponseDeclaration],
) -> tuple[str, _ResponseDeclaration]:
    response_identifier = element.get("response-identifier")
    declaration = declarations.get(response_identifier) if response_identifier else None
    if response_identifier is None or declaration is None:
        raise _UnsupportedInteraction
    return response_identifier, declaration


def _choice(element: ElementTree.Element) -> ExamNetQtiChoice:
    body = read_text_paragraphs(element)
    return ExamNetQtiChoice(
        identifier=element.get("identifier") or "",
        text=_plain_text(body),
        body=body,
    )


def _match_entry(element: ElementTree.Element) -> ExamNetQtiMatchEntry:
    body = read_text_paragraphs(element)
    return ExamNetQtiMatchEntry(
        identifier=element.get("identifier") or "",
        text=_plain_text(body),
        body=body,
    )


def _item(
    root: ElementTree.Element,
    *,
    sequence: int,
    interaction_type: ExamNetQtiInteractionType,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    evaluation_mode: ExamNetQtiEvaluationMode = ExamNetQtiEvaluationMode.AUTOMATIC,
    free_text_criterion_points: int | float | None = None,
    choices: tuple[ExamNetQtiChoice, ...] = (),
    correct_choice_identifiers: tuple[str, ...] = (),
    text_entry_gaps: tuple[ExamNetQtiTextEntryGap, ...] = (),
    inline_choice_gaps: tuple[ExamNetQtiInlineChoiceGap, ...] = (),
    match_pairs: tuple[ExamNetQtiMatchPair, ...] = (),
    match_left: tuple[ExamNetQtiMatchEntry, ...] = (),
    match_right: tuple[ExamNetQtiMatchEntry, ...] = (),
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=root.get("identifier") or "",
        sequence=sequence,
        title=root.get("title") or "",
        interaction_type=interaction_type,
        prompt_lines=_prompt_lines(prompt_paragraphs),
        max_score=max_score,
        prompt_paragraphs=prompt_paragraphs,
        evaluation_mode=evaluation_mode,
        free_text_criterion_points=free_text_criterion_points,
        choices=choices,
        correct_choice_identifiers=correct_choice_identifiers,
        text_entry_gaps=text_entry_gaps,
        inline_choice_gaps=inline_choice_gaps,
        match_pairs=match_pairs,
        match_left=match_left,
        match_right=match_right,
        image_resources=image_resources,
    )


def _prompt_lines(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> tuple[str, ...]:
    return tuple(line for line in paragraphs_plain_text(paragraphs).splitlines() if line.strip())


def _plain_text(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> str:
    return " ".join(paragraphs_plain_text(paragraphs).split())


def _image_resources(
    elements: tuple[ElementTree.Element, ...],
    *,
    item_path: str,
    files: Mapping[str, bytes],
) -> tuple[ExamNetQtiImageResource, ...]:
    base_dir = posixpath.dirname(item_path)
    resources: list[ExamNetQtiImageResource] = []
    for number, element in enumerate(elements, start=1):
        source = element.get("src")
        if not source:
            raise _UnsupportedImage
        path = posixpath.normpath(posixpath.join(base_dir, source))
        payload = files.get(path)
        if payload is None:
            raise _UnsupportedImage
        media_type = _media_type(payload)
        if media_type is None:
            raise _UnsupportedImage
        resources.append(
            ExamNetQtiImageResource(
                asset_id=f"image_{number:03d}",
                filename=posixpath.basename(path),
                media_type=media_type,
                payload=payload,
                alt_text=element.get("alt", ""),
                source_reference=path,
            )
        )
    return tuple(resources)


def _media_type(payload: bytes) -> str | None:
    if payload.startswith(_PNG_SIGNATURE):
        return "image/png"
    if payload.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    return None


def _response_declarations(
    root: ElementTree.Element,
) -> dict[str, _ResponseDeclaration]:
    declarations: dict[str, _ResponseDeclaration] = {}
    for element in root.findall(qti_tag("qti-response-declaration")):
        identifier = element.get("identifier")
        if not identifier:
            continue
        declarations[identifier] = _response_declaration(element)
    return declarations


def _response_declaration(element: ElementTree.Element) -> _ResponseDeclaration:
    correct_response = element.find(qti_tag("qti-correct-response"))
    correct_values: tuple[str, ...] = ()
    if correct_response is not None:
        correct_values = tuple(
            (value.text or "").strip() for value in correct_response.findall(qti_tag("qti-value"))
        )
    mapping_element = element.find(qti_tag("qti-mapping"))
    mapping: _Mapping | None = None
    if mapping_element is not None:
        mapping = _Mapping(
            upper_bound=mapping_element.get("upper-bound"),
            entries=tuple(
                _MappingEntry(
                    map_key=entry.get("map-key") or "",
                    mapped_value=entry.get("mapped-value") or "",
                )
                for entry in mapping_element.findall(qti_tag("qti-map-entry"))
            ),
        )
    return _ResponseDeclaration(
        cardinality=element.get("cardinality") or "",
        base_type=element.get("base-type") or "",
        correct_values=correct_values,
        mapping=mapping,
    )


def _max_score(root: ElementTree.Element) -> int | float | None:
    declaration = next(
        (
            element
            for element in root.findall(qti_tag("qti-outcome-declaration"))
            if element.get("identifier") == "MAXSCORE"
        ),
        None,
    )
    if declaration is None:
        return None
    default_value = declaration.find(qti_tag("qti-default-value"))
    if default_value is None:
        return None
    value = default_value.find(qti_tag("qti-value"))
    if value is None or value.text is None:
        return None
    number = _number(value.text)
    return None if number == 0 else number


def _number(text: str) -> int | float:
    return _to_number(_decimal(text))


def _decimal(text: str) -> Decimal:
    try:
        value = Decimal(text.strip())
    except InvalidOperation as error:
        raise _UnsupportedInteraction from error
    if not value.is_finite():
        raise _UnsupportedInteraction
    return value


def _to_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _unsupported_item(
    root: ElementTree.Element,
    sequence: int,
    reason: ExamNetQtiUnsupportedReason,
) -> ExamNetQtiUnsupportedItem:
    body = root.find(qti_tag("qti-item-body"))
    node = body if body is not None else root
    opening_text = " ".join("".join(node.itertext()).split())[:_OPENING_TEXT_LIMIT]
    return ExamNetQtiUnsupportedItem(
        sequence=sequence,
        opening_text=opening_text,
        reason=reason,
    )


def _local_name(tag: str) -> str:
    if not tag.startswith("{"):
        return tag
    return tag.rsplit("}", 1)[-1]
