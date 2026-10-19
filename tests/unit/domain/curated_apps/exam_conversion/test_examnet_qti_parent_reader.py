"""Round-trip and fail-closed tests for the QTI parent item reader.

Purpose:
    Prove that `examnet_qti_item_reader` inverts the writer's shared-instruction
    layout: a parent item reads back as one item whose children carry their own
    interaction, prompt, points, keys and image indexes, while each unsupported
    child is skipped with its own note after the parent.

Relationships:
    - Builds native documents with parents using the existing exam-workspace
      builders and exports them through `native_exam_to_examnet_qti_items`.
    - Reads the serialized items back with `read_examnet_qti_item`.
"""

from __future__ import annotations

import hashlib
from typing import Literal
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
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
    review_complete,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)

pytestmark = pytest.mark.unit

_QTI = f"{{{QTI_NAMESPACE}}}"
_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg"}
_PNG_A = b"\x89PNG\r\n\x1a\npayload-a"
_PNG_B = b"\x89PNG\r\n\x1a\npayload-b"
_PNG_C = b"\x89PNG\r\n\x1a\npayload-c"


def _tag(local_name: str) -> str:
    return f"{_QTI}{local_name}"


def _paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))


def _parent(children: tuple[NativeExamItem, ...], *, instruction: str = "Gör alla deluppgifter."):
    return NativeExamParent(
        parent_id="parent_001",
        place=min(child.sequence for child in children) - 1,
        instruction=(_paragraph(instruction),),
        item_ids=tuple(child.item_id for child in children),
    )


def _document(
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


def _unkeyed_choice_child(*, sequence: int, item_id: str, points: int) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=plain_body(f"Välj ett alternativ för fråga {sequence}."),
        points=points,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
            NativeChoice(choice_id="choice_002", body=plain_body("Två")),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        review=review_complete(),
    )


def _gap_fill_child(
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


def _asset(asset_id: str, payload: bytes, media_type: Literal["image/png", "image/jpeg"]):
    return NativeExamAsset(
        asset_id=asset_id,
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type=media_type,
        byte_length=len(payload),
    )


def _export(
    document: NativeExamDocument, *, assets_by_id: dict[str, bytes]
) -> tuple[ExamNetQtiItem, ...]:
    return native_exam_to_examnet_qti_items(document, assets_by_id=assets_by_id)


def _round_trip(
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


def _child_projection(item: ExamNetQtiItem) -> tuple[object, ...]:
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


def _image_payloads(item: ExamNetQtiItem) -> tuple[tuple[str, bytes], ...]:
    return tuple((image.media_type, image.payload) for image in item.image_resources)


# --- the mixed parent --------------------------------------------------------------------


def test_a_mixed_parent_reads_back_every_child_and_the_shared_instruction() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_gap_fill_item(sequence=2, item_id="item_002"),
        make_free_text_item(sequence=3, item_id="item_003"),
        inline_choice_item(sequence=4, points=2),
    )
    (exported,) = _export(_document(children, parent=_parent(children)), assets_by_id={})

    read = _round_trip((exported,))

    assert len(read) == 1
    (parent,) = read
    assert isinstance(parent, ExamNetQtiItem)
    assert parent.item_id == "parent_001"
    assert parent.sequence == 1
    assert parent.interaction_type is exported.interaction_type
    assert parent.title == exported.title
    assert parent.prompt_paragraphs == exported.prompt_paragraphs
    assert parent.instruction_lines == exported.instruction_lines
    assert parent.max_score == exported.max_score == 9
    assert parent.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
    assert len(parent.children) == len(exported.children) == 4
    for export_child, read_child in zip(exported.children, parent.children, strict=True):
        assert read_child.item_id == f"parent_001_child_{read_child.sequence}"
        assert _child_projection(read_child) == _child_projection(export_child)


def test_a_matching_child_round_trips_its_lists_and_pairs() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        matching_item(sequence=2, item_id="item_002"),
    )
    (exported,) = _export(_document(children, parent=_parent(children)), assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 2
    assert parent.children[1].max_score == 3
    assert _child_projection(parent.children[1]) == _child_projection(exported.children[1])


def test_a_parent_with_only_a_gap_fill_child_reads_as_one_separator_child() -> None:
    child = _gap_fill_child(sequence=1, item_id="item_001", points=2, gap_count=1)
    document = _document((child,), parent=_parent((child,)))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 1
    (read_child,) = parent.children
    assert read_child.interaction_type is ExamNetQtiInteractionType.GAP_FILL
    assert read_child.max_score == 2
    assert _child_projection(read_child) == _child_projection(exported.children[0])


# --- child points ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("points", "gap_count", "expected"),
    [(1, 3, 1), (2.5, 2, 2.5), (1, 2, 1), (2, 3, 2), (0.5, 1, 0.5), (3, 1, 3)],
)
def test_a_gap_child_recovers_its_points_from_the_rounded_share(
    points: int | float, gap_count: int, expected: int | float
) -> None:
    child = _gap_fill_child(sequence=1, item_id="item_001", points=points, gap_count=gap_count)
    document = _document((child,), parent=_parent((child,)))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    (read_child,) = parent.children
    assert read_child.max_score == expected
    assert type(read_child.max_score) is type(expected)


def test_an_inline_choice_child_recovers_its_points_from_its_gap_shares() -> None:
    child = inline_choice_item(sequence=1)
    child = child.model_copy(update={"points": 3})
    document = _document((child,), parent=_parent((child,)))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    (read_child,) = parent.children
    assert read_child.max_score == 3
    assert _child_projection(read_child) == _child_projection(exported.children[0])


def test_a_child_without_a_key_takes_the_parents_remainder() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        _unkeyed_choice_child(sequence=2, item_id="item_002", points=2),
    )
    document = _document(children, parent=_parent(children))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert exported.max_score == 3
    keyed, unkeyed = parent.children
    assert keyed.max_score == 1
    assert unkeyed.max_score == 2


def test_two_children_without_keys_keep_no_points() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        _unkeyed_choice_child(sequence=2, item_id="item_002", points=2),
        _unkeyed_choice_child(sequence=3, item_id="item_003", points=3),
    )
    document = _document(children, parent=_parent(children))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert exported.max_score == 6
    assert [child.max_score for child in parent.children] == [1, None, None]


# --- images ------------------------------------------------------------------------------


def _imaged_choice(*, sequence: int, item_id: str, asset_id: str) -> NativeExamItem:
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


def test_instruction_and_child_pictures_keep_their_own_indexes() -> None:
    payloads = {
        "asset_00000000000000a1": _PNG_A,
        "asset_00000000000000b2": _PNG_B,
        "asset_00000000000000c3": _PNG_C,
    }
    assets = tuple(_asset(asset_id, payload, "image/png") for asset_id, payload in payloads.items())
    stem_asset, first_asset, second_asset = payloads
    children = (
        _imaged_choice(sequence=1, item_id="item_001", asset_id=first_asset),
        _imaged_choice(sequence=2, item_id="item_002", asset_id=second_asset),
    )
    instruction = NativeExamParent(
        parent_id="parent_001",
        place=children[0].sequence - 1,
        instruction=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Se bilden: ", marks=()),
                    NativeAssetSegment(asset_id=stem_asset),
                ),
            ),
        ),
        item_ids=tuple(child.item_id for child in children),
    )
    document = _document(children, parent=instruction, assets=assets)
    (exported,) = _export(document, assets_by_id=payloads)

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert _image_payloads(parent) == _image_payloads(exported)
    assert parent.image_resources[0].payload == _PNG_A
    assert parent.children[0].image_resources[0].payload == _PNG_B
    assert parent.children[1].image_resources[0].payload == _PNG_C
    # every prompt image index addresses the item's own resources from zero
    assert _image_indexes(parent.prompt_paragraphs) == [0]
    assert _image_indexes(parent.children[0].prompt_paragraphs) == [0]
    assert _image_indexes(parent.children[1].prompt_paragraphs) == [0]
    assert _child_projection(parent.children[0]) == _child_projection(exported.children[0])
    assert _child_projection(parent.children[1]) == _child_projection(exported.children[1])


def _image_indexes(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> list[int]:
    return [
        segment.image_index
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, ExamNetQtiPromptImage)
    ]


# --- unsupported children ----------------------------------------------------------------


def _serialized_parent(*children: NativeExamItem) -> bytes:
    document = _document(children, parent=_parent(children))
    (exported,) = _export(document, assets_by_id={})
    return serialize_qti_assessment_item(exported)


def test_a_slider_child_is_skipped_with_one_note_after_the_parent() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    ElementTree.SubElement(
        body, _tag("qti-slider-interaction"), {"response-identifier": "item_003_RESPONSE"}
    )
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 2
    parent, note = read
    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 2
    assert isinstance(note, ExamNetQtiUnsupportedItem)
    assert note.sequence == parent.sequence == 1
    assert note.reason is ExamNetQtiUnsupportedReason.INTERACTION


def test_a_gap_inside_the_instruction_makes_the_whole_item_unsupported() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    paragraph = ElementTree.Element(_tag("p"))
    ElementTree.SubElement(
        paragraph, _tag("qti-text-entry-interaction"), {"response-identifier": "GAP"}
    )
    body.insert(0, paragraph)
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 1
    (unsupported,) = read
    assert isinstance(unsupported, ExamNetQtiUnsupportedItem)
    assert unsupported.reason is ExamNetQtiUnsupportedReason.INTERACTION


def test_a_picture_inside_the_instruction_makes_the_whole_item_unsupported() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    paragraph = ElementTree.Element(_tag("p"))
    ElementTree.SubElement(paragraph, _tag("img"), {"src": "images/missing.png", "alt": "Bild"})
    body.insert(0, paragraph)
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 1
    (unsupported,) = read
    assert isinstance(unsupported, ExamNetQtiUnsupportedItem)
    assert unsupported.reason is ExamNetQtiUnsupportedReason.IMAGE


def test_a_child_picture_that_cannot_be_resolved_skips_only_that_child() -> None:
    payloads = {"asset_00000000000000a1": _PNG_A}
    assets = (_asset("asset_00000000000000a1", _PNG_A, "image/png"),)
    children = (
        _imaged_choice(sequence=1, item_id="item_001", asset_id="asset_00000000000000a1"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    document = _document(children, parent=_parent(children), assets=assets)
    (exported,) = _export(document, assets_by_id=payloads)
    xml = serialize_qti_assessment_item(exported, image_paths=("images/parent_001-001.png",))
    read = _read(xml)

    assert len(read) == 2
    parent, note = read
    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 1
    assert isinstance(note, ExamNetQtiUnsupportedItem)
    assert note.sequence == parent.sequence
    assert note.reason is ExamNetQtiUnsupportedReason.IMAGE


def test_an_item_with_only_unsupported_children_returns_only_their_notes() -> None:
    root = ElementTree.Element(
        _tag("qti-assessment-item"), {"identifier": "item_001", "title": "Fråga"}
    )
    body = ElementTree.SubElement(root, _tag("qti-item-body"))
    ElementTree.SubElement(body, _tag("qti-slider-interaction"), {"response-identifier": "FIRST"})
    ElementTree.SubElement(body, _tag("qti-slider-interaction"), {"response-identifier": "SECOND"})
    read = _read(ElementTree.tostring(root, encoding="utf-8"), sequence=4)

    assert len(read) == 2
    assert all(isinstance(item, ExamNetQtiUnsupportedItem) for item in read)
    assert [item.sequence for item in read] == [4, 4]
    assert all(
        isinstance(item, ExamNetQtiUnsupportedItem)
        and item.reason is ExamNetQtiUnsupportedReason.INTERACTION
        for item in read
    )


def test_a_skipped_middle_child_keeps_the_later_children_positions() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    slider = ElementTree.Element(_tag("qti-slider-interaction"), {"response-identifier": "EXTRA"})
    body.insert(2, slider)
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 2
    parent, note = read
    assert isinstance(parent, ExamNetQtiItem)
    assert [child.item_id for child in parent.children] == [
        "parent_001_child_1",
        "parent_001_child_3",
    ]
    assert [child.sequence for child in parent.children] == [1, 3]
    assert isinstance(note, ExamNetQtiUnsupportedItem)
    assert note.sequence == parent.sequence


def _manual_parent_xml() -> bytes:
    """One parent whose three scoring routes disagree: all-or-nothing, mapping, remainder."""

    root = ElementTree.Element(
        _tag("qti-assessment-item"), {"identifier": "item_001", "title": "Del B"}
    )
    first = ElementTree.SubElement(
        root,
        _tag("qti-response-declaration"),
        {"identifier": "FIRST", "cardinality": "multiple", "base-type": "identifier"},
    )
    correct = ElementTree.SubElement(first, _tag("qti-correct-response"))
    for value in ("choice_001", "choice_002"):
        ElementTree.SubElement(correct, _tag("qti-value")).text = value
    for gap_identifier in ("G1", "G2"):
        declaration = ElementTree.SubElement(
            root,
            _tag("qti-response-declaration"),
            {"identifier": gap_identifier, "cardinality": "single", "base-type": "string"},
        )
        mapping = ElementTree.SubElement(
            declaration,
            _tag("qti-mapping"),
            {"default-value": "0", "lower-bound": "0", "upper-bound": "1"},
        )
        ElementTree.SubElement(
            mapping,
            _tag("qti-map-entry"),
            {"map-key": f"svar-{gap_identifier}", "mapped-value": "1"},
        )
    mapped = ElementTree.SubElement(
        root,
        _tag("qti-response-declaration"),
        {"identifier": "MAPPED", "cardinality": "single", "base-type": "identifier"},
    )
    mapped_correct = ElementTree.SubElement(mapped, _tag("qti-correct-response"))
    ElementTree.SubElement(mapped_correct, _tag("qti-value")).text = "choice_001"
    mapped_mapping = ElementTree.SubElement(
        mapped,
        _tag("qti-mapping"),
        {"default-value": "0", "lower-bound": "0", "upper-bound": "2"},
    )
    ElementTree.SubElement(
        mapped_mapping,
        _tag("qti-map-entry"),
        {"map-key": "choice_001", "mapped-value": "2"},
    )
    ElementTree.SubElement(
        root,
        _tag("qti-response-declaration"),
        {"identifier": "SECOND", "cardinality": "single", "base-type": "string"},
    )
    outcome = ElementTree.SubElement(
        root,
        _tag("qti-outcome-declaration"),
        {"identifier": "MAXSCORE", "cardinality": "single", "base-type": "float"},
    )
    default_value = ElementTree.SubElement(outcome, _tag("qti-default-value"))
    ElementTree.SubElement(default_value, _tag("qti-value")).text = "11"
    processing = ElementTree.SubElement(root, _tag("qti-response-processing"))
    condition = ElementTree.SubElement(processing, _tag("qti-response-condition"))
    response_if = ElementTree.SubElement(condition, _tag("qti-response-if"))
    match = ElementTree.SubElement(response_if, _tag("qti-match"))
    ElementTree.SubElement(match, _tag("qti-variable"), {"identifier": "FIRST"})
    ElementTree.SubElement(match, _tag("qti-correct"), {"identifier": "FIRST"})
    set_outcome = ElementTree.SubElement(
        response_if, _tag("qti-set-outcome-value"), {"identifier": "SCORE"}
    )
    total = ElementTree.SubElement(set_outcome, _tag("qti-sum"))
    ElementTree.SubElement(total, _tag("qti-variable"), {"identifier": "SCORE"})
    ElementTree.SubElement(total, _tag("qti-base-value"), {"base-type": "float"}).text = "3"
    mapped_condition = ElementTree.SubElement(processing, _tag("qti-response-condition"))
    mapped_if = ElementTree.SubElement(mapped_condition, _tag("qti-response-if"))
    not_null = ElementTree.SubElement(mapped_if, _tag("qti-not"))
    is_null = ElementTree.SubElement(not_null, _tag("qti-is-null"))
    ElementTree.SubElement(is_null, _tag("qti-variable"), {"identifier": "MAPPED"})
    mapped_set = ElementTree.SubElement(
        mapped_if, _tag("qti-set-outcome-value"), {"identifier": "SCORE"}
    )
    mapped_total = ElementTree.SubElement(mapped_set, _tag("qti-sum"))
    ElementTree.SubElement(mapped_total, _tag("qti-variable"), {"identifier": "SCORE"})
    ElementTree.SubElement(mapped_total, _tag("qti-map-response"), {"identifier": "MAPPED"})
    body = ElementTree.SubElement(root, _tag("qti-item-body"))
    instruction = ElementTree.SubElement(body, _tag("p"))
    instruction.text = "Gör alla deluppgifter."
    choice = ElementTree.SubElement(
        body,
        _tag("qti-choice-interaction"),
        {"response-identifier": "FIRST", "max-choices": "2"},
    )
    choice_prompt = ElementTree.SubElement(choice, _tag("qti-prompt"))
    ElementTree.SubElement(choice_prompt, _tag("p")).text = "Markera två."
    for identifier in ("choice_001", "choice_002"):
        simple = ElementTree.SubElement(
            choice, _tag("qti-simple-choice"), {"identifier": identifier}
        )
        simple.text = "Alt"
    ElementTree.SubElement(body, _tag("qti-gap-match-interaction"), {"response-identifier": "GAPS"})
    gap_paragraph = ElementTree.SubElement(body, _tag("p"))
    for gap_identifier in ("G1", "G2"):
        ElementTree.SubElement(
            gap_paragraph,
            _tag("qti-text-entry-interaction"),
            {"response-identifier": gap_identifier, "expected-length": "10"},
        )
    mapped_choice = ElementTree.SubElement(
        body,
        _tag("qti-choice-interaction"),
        {"response-identifier": "MAPPED", "max-choices": "1"},
    )
    mapped_prompt = ElementTree.SubElement(mapped_choice, _tag("qti-prompt"))
    ElementTree.SubElement(mapped_prompt, _tag("p")).text = "Välj ett."
    mapped_simple = ElementTree.SubElement(
        mapped_choice, _tag("qti-simple-choice"), {"identifier": "choice_001"}
    )
    mapped_simple.text = "Ett"
    extended = ElementTree.SubElement(
        body,
        _tag("qti-extended-text-interaction"),
        {"response-identifier": "SECOND", "expected-lines": "8"},
    )
    extended_prompt = ElementTree.SubElement(extended, _tag("qti-prompt"))
    ElementTree.SubElement(extended_prompt, _tag("p")).text = "Resonera."
    ElementTree.indent(root, space="  ")
    payload = ElementTree.tostring(root, encoding="utf-8")
    assert isinstance(payload, bytes)
    return payload


def test_the_three_scoring_routes_read_their_own_points() -> None:
    read = _read(_manual_parent_xml())

    assert len(read) == 1
    (parent,) = read
    assert isinstance(parent, ExamNetQtiItem)
    assert parent.max_score == 11
    assert [child.max_score for child in parent.children] == [3, 2, 2, 4]


def _read(xml: bytes, *, sequence: int = 1) -> tuple[ExamNetQtiReadItem, ...]:
    return read_examnet_qti_item(
        xml=xml,
        item_path="items/item_001.xml",
        files={},
        sequence=sequence,
    )
