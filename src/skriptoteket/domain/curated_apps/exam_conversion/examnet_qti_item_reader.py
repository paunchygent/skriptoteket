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

from collections.abc import Mapping
from dataclasses import replace
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_block_item_reader import (
    read_block_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    ExamNetQtiUnsupportedContent,
    read_rich_content,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_gap_item_reader import (
    read_gap_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageSource,
    ExamNetQtiReadItem,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_scores import (
    ResponseDeclaration,
    max_score,
    response_declarations,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    BLOCK_INTERACTIONS,
    OPENING_TEXT_LIMIT,
    UnsupportedImage,
    UnsupportedInteraction,
    image_resources,
    item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_parent_layout_reader import (
    is_child_start,
    read_parent_layout,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)
from skriptoteket.domain.errors import validation_error

__all__ = [
    "read_examnet_qti_item",
    "read_examnet_qti_items",
]


_UNSAFE_XML = "QTI-paketet innehåller en otillåten XML-konstruktion."


_INVALID_ITEM_XML = "QTI-paketet innehåller en fråga som inte är giltig XML."


_UNSUPPORTED_VERSION = (
    "QTI-paketet använder en QTI-version som inte stöds. Endast QTI 3.0 kan importeras."
)


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
    except UnsupportedImage:
        return (_unsupported_item(root, sequence, ExamNetQtiUnsupportedReason.IMAGE),)
    except (ExamNetQtiUnsupportedContent, UnsupportedInteraction):
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
        raise UnsupportedInteraction

    declarations = response_declarations(root)
    item_max_score = max_score(root)

    information = _read_information_if_present(
        root,
        body=body,
        declarations=declarations,
        max_score=item_max_score,
        item_path=item_path,
        files=files,
        sequence=sequence,
    )
    if information is not None:
        return (information,)

    body_children = list(body)
    blocks = [element for element in body_children if element.tag in BLOCK_INTERACTIONS]
    starts = [element for element in body_children if is_child_start(element)]

    if len(blocks) == 1 and len(starts) == 1:
        return (
            read_block_item(
                root,
                body=body,
                block=blocks[0],
                declarations=declarations,
                max_score=item_max_score,
                item_path=item_path,
                files=files,
                sequence=sequence,
            ),
        )
    if not starts:
        return (
            read_gap_item(
                root,
                body=body,
                declarations=declarations,
                max_score=item_max_score,
                item_path=item_path,
                files=files,
                sequence=sequence,
            ),
        )
    return read_parent_layout(
        root,
        body=body,
        declarations=declarations,
        max_score=item_max_score,
        item_path=item_path,
        files=files,
        sequence=sequence,
    )


def _read_information_if_present(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    declarations: Mapping[str, ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem | None:
    """Return the information block when the body holds only prompt content.

    Structural decision only: no response declaration and no interaction element
    anywhere in the body. An empty body keeps the caller's unsupported path.
    """

    if declarations:
        return None
    for element in body.iter():
        tag = element.tag
        if isinstance(tag, str) and tag.rsplit("}", 1)[-1].endswith("-interaction"):
            return None
    read_body = read_rich_content(list(body), leading_text=body.text)
    if not read_body.paragraphs:
        return None
    resolved_images = image_resources(read_body.image_elements, item_path=item_path, files=files)
    built = item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.INFORMATION,
        prompt_paragraphs=read_body.paragraphs,
        image_resources=resolved_images,
        max_score=max_score,
    )
    return replace(built, instruction_lines=built.prompt_lines)


def _unsupported_item(
    root: ElementTree.Element,
    sequence: int,
    reason: ExamNetQtiUnsupportedReason,
) -> ExamNetQtiUnsupportedItem:
    body = root.find(qti_tag("qti-item-body"))
    node = body if body is not None else root
    opening_text = " ".join("".join(node.itertext()).split())[:OPENING_TEXT_LIMIT]
    return ExamNetQtiUnsupportedItem(
        sequence=sequence,
        opening_text=opening_text,
        reason=reason,
    )
