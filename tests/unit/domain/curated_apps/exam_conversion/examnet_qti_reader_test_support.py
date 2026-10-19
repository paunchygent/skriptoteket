"""Shared builders for the split Exam.net QTI reader tests.

Purpose:
    Hold the item, parent-layout and body-reader builders used by more than
    one ``test_examnet_qti_*`` module so the split files import them instead
    of copying them. Test bodies keep calling their original short names
    through ``import ... as ...`` aliases.

Relationships:
    - Imported by ``test_examnet_qti_item_reader.py``,
      ``test_examnet_qti_item_block.py``, ``test_examnet_qti_item_gap.py``,
      ``test_examnet_qti_parent_reader.py``,
      ``test_examnet_qti_parent_scores.py``,
      ``test_examnet_qti_parent_unsupported.py``,
      ``test_examnet_qti_body_reader.py`` and
      ``test_examnet_qti_body_refusal.py``.
"""

from __future__ import annotations

import hashlib
from typing import Literal
from uuid import uuid4
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptParagraph,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiReadItem,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_reader import (
    read_examnet_qti_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
    review_complete,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_single_choice_item,
    plain_body,
)

_QTI = f"{{{QTI_NAMESPACE}}}"
_ITEM_PATH = "items/item_001.xml"
_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg"}


def make_asset(
    asset_id: str,
    payload: bytes,
    media_type: Literal["image/png", "image/jpeg"],
) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=asset_id,
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type=media_type,
        byte_length=len(payload),
    )


def item_round_trip(
    item: NativeExamItem,
    *,
    image_paths: tuple[str, ...] = (),
    files: dict[str, bytes] | None = None,
    assets: tuple[NativeExamAsset, ...] = (),
    payloads: dict[str, bytes] | None = None,
) -> tuple[ExamNetQtiItem, ExamNetQtiItem]:
    document = document_of((item,), assets=assets)
    (exported,) = native_exam_to_examnet_qti_items(document, assets_by_id=payloads or {})
    xml = serialize_qti_assessment_item(exported, image_paths=image_paths)
    (read,) = read_examnet_qti_item(
        xml=xml,
        item_path=_ITEM_PATH,
        files=files or {},
        sequence=item.sequence,
    )
    assert isinstance(read, ExamNetQtiItem)
    return exported, read


def xml_root(
    *,
    identifier: str = "item_001",
    title: str = "Fråga",
    namespace: str = QTI_NAMESPACE,
) -> ElementTree.Element:
    return ElementTree.Element(
        f"{{{namespace}}}qti-assessment-item",
        {"identifier": identifier, "title": title},
    )


def xml_declaration(
    root: ElementTree.Element,
    *,
    identifier: str = "RESPONSE",
    cardinality: str = "single",
    base_type: str = "string",
    correct: tuple[str, ...] = (),
    mapping_entries: tuple[tuple[str, str], ...] | None = None,
) -> ElementTree.Element:
    declaration = ElementTree.SubElement(
        root,
        f"{_QTI}qti-response-declaration",
        {
            "identifier": identifier,
            "cardinality": cardinality,
            "base-type": base_type,
        },
    )
    if correct:
        correct_response = ElementTree.SubElement(declaration, f"{_QTI}qti-correct-response")
        for value in correct:
            ElementTree.SubElement(correct_response, f"{_QTI}qti-value").text = value
    if mapping_entries is not None:
        mapping = ElementTree.SubElement(
            declaration,
            f"{_QTI}qti-mapping",
            {"default-value": "0", "lower-bound": "0", "upper-bound": "1"},
        )
        for map_key, mapped_value in mapping_entries:
            ElementTree.SubElement(
                mapping,
                f"{_QTI}qti-map-entry",
                {"map-key": map_key, "mapped-value": mapped_value},
            )
    return declaration


def xml_max_score(root: ElementTree.Element, value: str = "1") -> None:
    outcome = ElementTree.SubElement(
        root,
        f"{_QTI}qti-outcome-declaration",
        {"identifier": "MAXSCORE", "cardinality": "single", "base-type": "float"},
    )
    default_value = ElementTree.SubElement(outcome, f"{_QTI}qti-default-value")
    ElementTree.SubElement(default_value, f"{_QTI}qti-value").text = value


def xml_body(root: ElementTree.Element) -> ElementTree.Element:
    return ElementTree.SubElement(root, f"{_QTI}qti-item-body")


def xml_bytes(root: ElementTree.Element) -> bytes:
    ElementTree.indent(root, space="  ")
    payload = ElementTree.tostring(root, encoding="utf-8")
    assert isinstance(payload, bytes)
    return payload


def item_read_root(
    root: ElementTree.Element,
    *,
    sequence: int = 1,
    files: dict[str, bytes] | None = None,
) -> tuple[object, ...]:
    return read_examnet_qti_item(
        xml=xml_bytes(root),
        item_path=_ITEM_PATH,
        files=files or {},
        sequence=sequence,
    )


def item_unsupported(
    root: ElementTree.Element,
    *,
    reason: ExamNetQtiUnsupportedReason = ExamNetQtiUnsupportedReason.INTERACTION,
    sequence: int = 1,
    files: dict[str, bytes] | None = None,
) -> ExamNetQtiUnsupportedItem:
    (read,) = item_read_root(root, sequence=sequence, files=files)
    assert isinstance(read, ExamNetQtiUnsupportedItem)
    assert read.reason is reason
    assert read.sequence == sequence
    return read


def multiple_response_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.MULTIPLE_RESPONSE,
        body=plain_body("Markera alla rätt."),
        points=3,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
            NativeChoice(choice_id="choice_002", body=plain_body("Två")),
            NativeChoice(choice_id="choice_003", body=plain_body("Tre")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_001", "choice_003"),
        ),
        review=review_complete(),
    )


def qti_tag(local_name: str) -> str:
    return f"{_QTI}{local_name}"


def parent_paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))


def parent_of(children: tuple[NativeExamItem, ...], *, instruction: str = "Gör alla deluppgifter."):
    return NativeExamParent(
        parent_id="parent_001",
        place=min(child.sequence for child in children) - 1,
        instruction=(parent_paragraph(instruction),),
        item_ids=tuple(child.item_id for child in children),
    )


def parent_document(
    children: tuple[NativeExamItem, ...],
    *,
    parent: NativeExamParent,
    assets: tuple[NativeExamAsset, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=children,
        parents=(parent,),
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def parent_gap_fill_child(
    *, sequence: int, item_id: str, points: int | float, gap_count: int
) -> NativeExamItem:
    segments: list[NativeTextSegment | NativeGapSegment] = []
    gaps: list[NativeGap] = []
    for index in range(1, gap_count + 1):
        segments.append(NativeTextSegment(text=f"Frastyp {index}: ", marks=()))
        segments.append(NativeGapSegment(gap_id=f"gap_{index:03d}"))
        gaps.append(NativeGap(gap_id=f"gap_{index:03d}", accepted_values=(f"NF{index}",)))
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=(NativeParagraph(heading_level=None, segments=tuple(segments)),),
        points=points,
        gaps=tuple(gaps),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=review_complete(),
    )


def parent_export(
    document: NativeExamDocument, *, assets_by_id: dict[str, bytes]
) -> tuple[ExamNetQtiItem, ...]:
    return native_exam_to_examnet_qti_items(document, assets_by_id=assets_by_id)


def parent_round_trip(
    items: tuple[ExamNetQtiItem, ...],
) -> tuple[ExamNetQtiReadItem, ...]:
    """Serialize like the package does, then read every item back in test order."""

    files: dict[str, bytes] = {}
    read: list[ExamNetQtiReadItem] = []
    for sequence, item in enumerate(items, start=1):
        image_paths = tuple(
            f"images/{item.item_id}-{index:03d}{_EXTENSIONS[resource.media_type]}"
            for index, resource in enumerate(item.image_resources, start=1)
        )
        for path, resource in zip(image_paths, item.image_resources, strict=True):
            files[f"items/{path}"] = resource.payload
        xml = serialize_qti_assessment_item(item, image_paths=image_paths)
        read.extend(
            read_examnet_qti_item(
                xml=xml,
                item_path=f"items/{item.item_id}.xml",
                files=files,
                sequence=sequence,
            )
        )
    return tuple(read)


def child_projection(item: ExamNetQtiItem) -> tuple[object, ...]:
    return (
        item.interaction_type,
        item.prompt_paragraphs,
        item.max_score,
        item.evaluation_mode,
        item.free_text_criterion_points,
        tuple((choice.identifier, choice.text, choice.body) for choice in item.choices),
        item.correct_choice_identifiers,
        tuple(gap.accepted_values for gap in item.text_entry_gaps),
        tuple(
            (
                tuple((option.identifier, option.text, option.body) for option in gap.options),
                gap.correct_option_identifier,
            )
            for gap in item.inline_choice_gaps
        ),
        item.match_left,
        item.match_right,
        item.match_pairs,
        tuple((image.media_type, image.payload) for image in item.image_resources),
    )


def imaged_choice(*, sequence: int, item_id: str, asset_id: str) -> NativeExamItem:
    base = make_single_choice_item(sequence=sequence, item_id=item_id)
    return base.model_copy(
        update={
            "body": (
                *base.body,
                NativeParagraph(
                    heading_level=None, segments=(NativeAssetSegment(asset_id=asset_id),)
                ),
            )
        }
    )


def parent_read(xml: bytes, *, sequence: int = 1) -> tuple[ExamNetQtiReadItem, ...]:
    return read_examnet_qti_item(
        xml=xml,
        item_path="items/item_001.xml",
        files={},
        sequence=sequence,
    )


def body_roundtrip(root: ElementTree.Element) -> ElementTree.Element:
    """Indent and serialize exactly as the export does, then parse back."""

    ElementTree.indent(root, space="  ")
    xml_bytes = ElementTree.tostring(root, encoding="utf-8")
    return ElementTree.fromstring(xml_bytes)


def body_prompt(root: ElementTree.Element) -> ElementTree.Element:
    prompt = root.find(f".//{qti_tag('qti-prompt')}")
    assert prompt is not None
    return prompt


def body_gap(number: int, accepted_values: tuple[str, ...]) -> ExamNetQtiTextEntryGap:
    return ExamNetQtiTextEntryGap(
        response_identifier=f"RESPONSE_gap_{number:03d}",
        label=f"Lucka {number}",
        accepted_values=accepted_values,
    )


def body_free_text(
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    *,
    text_entry_gaps: tuple[ExamNetQtiTextEntryGap, ...] = (),
    image_resources: tuple[ExamNetQtiImageResource, ...] = (),
    expected_lines: int = DEFAULT_WRITING_LINES,
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Beskriv.",),
        max_score=1,
        prompt_paragraphs=paragraphs,
        text_entry_gaps=text_entry_gaps,
        image_resources=image_resources,
        expected_lines=expected_lines,
    )


__all__ = [
    "body_free_text",
    "body_gap",
    "body_prompt",
    "body_roundtrip",
    "child_projection",
    "imaged_choice",
    "item_read_root",
    "item_round_trip",
    "item_unsupported",
    "make_asset",
    "multiple_response_item",
    "parent_document",
    "parent_export",
    "parent_gap_fill_child",
    "parent_of",
    "parent_paragraph",
    "parent_read",
    "parent_round_trip",
    "qti_tag",
    "xml_body",
    "xml_bytes",
    "xml_declaration",
    "xml_max_score",
    "xml_root",
]
