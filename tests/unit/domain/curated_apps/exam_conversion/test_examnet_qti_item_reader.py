"""Round-trip and fail-closed tests for the Exam.net QTI item reader.

Purpose:
    Prove that `examnet_qti_item_reader` inverts the writer's standalone item
    layouts for every governed interaction kind, keeps images and points, and
    turns unsupported or unsafe input into the documented validation errors and
    skipped items.

Relationships:
    - Builds native items with the existing exam-workspace test builders and
      exports them through `native_exam_to_examnet_qti_items`.
    - Reads the reference package fixture directly with `zipfile`.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageItemSource,
    ExamNetQtiPackageSource,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_reader import (
    read_examnet_qti_item,
    read_examnet_qti_items,
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
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    item_read_root as _read_root,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    item_round_trip as _round_trip,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    item_unsupported as _unsupported,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    make_asset as _asset,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    multiple_response_item as _multiple_response_item,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_body as _body,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_declaration as _declaration,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_max_score as _max_score,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_root as _root,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_ordering_item,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)

pytestmark = pytest.mark.unit

_ITEM_PATH = "items/item_001.xml"
_REFERENCE_PACKAGE = Path("tests/fixtures/exam_conversion/reference-qti-package.zip")
_ASSET_PNG = "asset_1111111111111111"
_PNG = b"\x89PNG\r\n\x1a\nfirst picture"
_QTI = f"{{{QTI_NAMESPACE}}}"


def _projection(item: ExamNetQtiItem) -> tuple[object, ...]:
    return (
        item.item_id,
        item.sequence,
        item.title,
        item.interaction_type,
        item.prompt_lines,
        item.prompt_paragraphs,
        item.max_score,
        item.evaluation_mode,
        item.free_text_criterion_points,
        tuple((choice.identifier, choice.text, choice.body) for choice in item.choices),
        item.correct_choice_identifiers,
        tuple((gap.response_identifier, gap.accepted_values) for gap in item.text_entry_gaps),
        tuple(
            (
                gap.response_identifier,
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


def _assert_round_trips(item: NativeExamItem) -> ExamNetQtiItem:
    exported, read = _round_trip(item)
    assert _projection(read) == _projection(exported)
    return read


def test_every_supported_standalone_kind_round_trips() -> None:
    items = (
        make_free_text_item(),
        make_single_choice_item(),
        _multiple_response_item(),
        make_gap_fill_item(),
        inline_choice_item(),
        matching_item(),
        make_ordering_item(),
    )

    for item in items:
        read = _assert_round_trips(item)
        assert read.sequence == item.sequence
        assert read.item_id == item.item_id


def test_unsafe_doctype_refuses_the_whole_package() -> None:
    xml = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE foo [<!ENTITY bar "baz">]>'
        b'<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"'
        b' identifier="item_001"><qti-item-body/></qti-assessment-item>'
    )

    with pytest.raises(DomainError) as exc_info:
        read_examnet_qti_item(
            xml=xml,
            item_path=_ITEM_PATH,
            files={},
            sequence=1,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == ("QTI-paketet innehåller en otillåten XML-konstruktion.")
    assert exc_info.value.details == {"path": _ITEM_PATH}


def test_a_non_qti_3_namespace_refuses_the_whole_package() -> None:
    root = _root(namespace="http://www.imsglobal.org/xsd/imsqtiasi_v2p1")

    with pytest.raises(DomainError) as exc_info:
        _read_root(root)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == (
        "QTI-paketet använder en QTI-version som inte stöds. Endast QTI 3.0 kan importeras."
    )
    assert exc_info.value.details == {"path": _ITEM_PATH}


def test_malformed_xml_refuses_the_whole_package() -> None:
    with pytest.raises(DomainError) as exc_info:
        read_examnet_qti_item(
            xml=b"<qti-assessment-item",
            item_path=_ITEM_PATH,
            files={},
            sequence=1,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == ("QTI-paketet innehåller en fråga som inte är giltig XML.")
    assert exc_info.value.details == {"path": _ITEM_PATH}


def test_a_slider_interaction_is_unsupported() -> None:
    root = _root()
    _declaration(root)
    body = _body(root)
    ElementTree.SubElement(
        body, f"{_QTI}qti-slider-interaction", {"response-identifier": "RESPONSE"}
    )

    unsupported = _unsupported(root)

    assert unsupported.opening_text == ""


def test_a_missing_image_file_is_an_image_note() -> None:
    root = _root()
    _declaration(root)
    _max_score(root)
    body = _body(root)
    interaction = ElementTree.SubElement(
        body,
        f"{_QTI}qti-extended-text-interaction",
        {"response-identifier": "RESPONSE"},
    )
    prompt = ElementTree.SubElement(interaction, f"{_QTI}qti-prompt")
    ElementTree.SubElement(
        prompt,
        f"{_QTI}img",
        {"src": "images/missing.png", "alt": "Bild"},
    )

    _unsupported(root, reason=ExamNetQtiUnsupportedReason.IMAGE)


def test_a_gif_payload_is_an_image_note() -> None:
    root = _root()
    _declaration(root)
    _max_score(root)
    body = _body(root)
    interaction = ElementTree.SubElement(
        body,
        f"{_QTI}qti-extended-text-interaction",
        {"response-identifier": "RESPONSE"},
    )
    prompt = ElementTree.SubElement(interaction, f"{_QTI}qti-prompt")
    ElementTree.SubElement(
        prompt,
        f"{_QTI}img",
        {"src": "images/animation.gif", "alt": "Bild"},
    )

    _unsupported(
        root,
        reason=ExamNetQtiUnsupportedReason.IMAGE,
        files={"items/images/animation.gif": b"GIF89a not supported"},
    )


def test_two_choice_interactions_read_as_one_parent_with_two_children() -> None:
    root = _root()
    _declaration(root, identifier="FIRST", base_type="identifier", correct=("choice_001",))
    _declaration(root, identifier="SECOND", base_type="identifier", correct=("choice_002",))
    body = _body(root)
    for response_identifier, choice_identifier in (
        ("FIRST", "choice_001"),
        ("SECOND", "choice_002"),
    ):
        interaction = ElementTree.SubElement(
            body,
            f"{_QTI}qti-choice-interaction",
            {"response-identifier": response_identifier, "max-choices": "1"},
        )
        ElementTree.SubElement(
            interaction,
            f"{_QTI}qti-simple-choice",
            {"identifier": choice_identifier},
        ).text = "Ett alternativ"

    (read,) = _read_root(root, sequence=4)

    assert isinstance(read, ExamNetQtiItem)
    assert read.item_id == "item_001"
    assert read.sequence == 4
    assert read.interaction_type is ExamNetQtiInteractionType.SINGLE_CHOICE
    assert [child.sequence for child in read.children] == [1, 2]
    assert [child.correct_choice_identifiers for child in read.children] == [
        ("choice_001",),
        ("choice_002",),
    ]
    assert all(child.max_score is None for child in read.children)


def test_a_gap_match_with_children_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="PAIR", cardinality="multiple", base_type="directedPair")
    body = _body(root)
    gap_match = ElementTree.SubElement(
        body, f"{_QTI}qti-gap-match-interaction", {"response-identifier": "PAIR"}
    )
    ElementTree.SubElement(
        gap_match,
        f"{_QTI}qti-simple-associable-choice",
        {"identifier": "choice_001", "match-max": "1"},
    ).text = "Ett"

    _unsupported(root)


def test_a_separator_child_without_a_declaration_is_one_note() -> None:
    root = _root()
    _max_score(root)
    body = _body(root)
    ElementTree.SubElement(
        body, f"{_QTI}qti-gap-match-interaction", {"response-identifier": "SEPARATOR"}
    )
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    ElementTree.SubElement(
        paragraph, f"{_QTI}qti-text-entry-interaction", {"response-identifier": "GAP"}
    )

    _unsupported(root, sequence=2)


def test_the_reference_package_reads_every_item_in_test_order() -> None:
    with zipfile.ZipFile(_REFERENCE_PACKAGE) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    item_paths = tuple(f"items/item_{number:03d}.xml" for number in range(1, 8))
    source = ExamNetQtiPackageSource(
        items=tuple(ExamNetQtiPackageItemSource(path=path, xml=files[path]) for path in item_paths),
        files=files,
    )

    read = read_examnet_qti_items(source)

    assert all(isinstance(item, ExamNetQtiItem) for item in read)
    assert [item.sequence for item in read] == list(range(1, 8))
    supported = [item for item in read if isinstance(item, ExamNetQtiItem)]
    assert len(supported) == len(read)
    assert [item.interaction_type for item in supported] == [
        ExamNetQtiInteractionType.FREE_TEXT,
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.GAP_FILL,
    ]
    assert [item.max_score for item in supported] == [5, 2, 2, 2, 4, 6, 3]


def _information_document() -> tuple[NativeExamDocument, dict[str, bytes]]:
    from uuid import uuid4

    instruction = (
        *plain_body("Läs igenom texten först."),
        NativeParagraph(
            heading_level=None,
            segments=(NativeAssetSegment(asset_id=_ASSET_PNG),),
        ),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov på svenska",
        items=(make_free_text_item(),),
        parents=(
            NativeExamParent(
                parent_id="parent_001",
                place=1,
                instruction=instruction,
                item_ids=(),
            ),
        ),
        assets=(_asset(_ASSET_PNG, _PNG, "image/png"),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return document, {_ASSET_PNG: _PNG}


def test_the_exact_information_xml_reads_as_information_with_text_and_picture() -> None:
    document, payloads = _information_document()
    (free_text, information) = native_exam_to_examnet_qti_items(document, assets_by_id=payloads)
    assert information.interaction_type is ExamNetQtiInteractionType.INFORMATION

    image_paths = ("images/information.png",)
    xml = serialize_qti_assessment_item(information, image_paths=image_paths)

    (read,) = read_examnet_qti_item(
        xml=xml,
        item_path=_ITEM_PATH,
        files={"items/images/information.png": _PNG},
        sequence=information.sequence,
    )

    assert isinstance(read, ExamNetQtiItem)
    assert read.interaction_type is ExamNetQtiInteractionType.INFORMATION
    assert read.sequence == information.sequence
    assert read.item_id == information.item_id
    assert read.max_score is None
    assert read.prompt_paragraphs == information.prompt_paragraphs
    assert "Läs igenom texten först." in "".join(
        segment.text
        for paragraph in read.prompt_paragraphs
        for segment in paragraph.segments
        if hasattr(segment, "text")
    )
    assert [image.payload for image in read.image_resources] == [_PNG]
    assert [image.media_type for image in read.image_resources] == ["image/png"]
    assert free_text.interaction_type is not ExamNetQtiInteractionType.INFORMATION


def test_a_text_paragraph_with_an_extended_text_interaction_is_not_information() -> None:
    root = _root()
    _declaration(root)
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    paragraph.text = "Resonera om texten."
    ElementTree.SubElement(
        body, f"{_QTI}qti-extended-text-interaction", {"response-identifier": "RESPONSE"}
    )

    (read,) = _read_root(root)

    assert isinstance(read, ExamNetQtiItem)
    assert read.interaction_type is ExamNetQtiInteractionType.FREE_TEXT


def test_an_empty_body_without_interaction_stays_unsupported() -> None:
    root = _root()
    _body(root)

    unsupported = _unsupported(root)

    assert unsupported.opening_text == ""
