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
    - Consumed by ``exam_workspace.qti_import``; parent items with several
      interactions or a gap-match separator arrive in a later unit.
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
    """Read one item; a tuple because a later unit may return a parent plus skipped children."""

    root = _parse_item(xml, item_path=item_path)
    try:
        return (
            _read_item(
                root,
                item_path=item_path,
                files=files,
                sequence=sequence,
            ),
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
) -> ExamNetQtiReadItem:
    body = root.find(qti_tag("qti-item-body"))
    if body is None:
        raise _UnsupportedInteraction

    body_children = list(body)
    blocks = [element for element in body_children if element.tag in _BLOCK_INTERACTIONS]
    has_separator = any(
        element.tag == _SEPARATOR and len(element) == 0 for element in body_children
    )
    declarations = _response_declarations(root)
    max_score = _max_score(root)

    if len(blocks) == 1 and not has_separator:
        return _read_block_item(
            root,
            body=body,
            block=blocks[0],
            declarations=declarations,
            max_score=max_score,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    if not blocks and not has_separator:
        return _read_gap_item(
            root,
            body=body,
            declarations=declarations,
            max_score=max_score,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    return _read_parent_layout(root, sequence=sequence)


def _read_parent_layout(
    root: ElementTree.Element,
    *,
    sequence: int,
) -> ExamNetQtiUnsupportedItem:
    """Parent items arrive in a later unit; until then the item is skipped."""

    return _unsupported_item(root, sequence, ExamNetQtiUnsupportedReason.INTERACTION)


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
    try:
        value = Decimal(text.strip())
    except InvalidOperation as error:
        raise _UnsupportedInteraction from error
    if not value.is_finite():
        raise _UnsupportedInteraction
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
