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

import hashlib
import zipfile
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageItemSource,
    ExamNetQtiPackageSource,
    ExamNetQtiUnsupportedItem,
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
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
    review_complete,
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
_ASSET_JPEG = "asset_2222222222222222"
_PNG = b"\x89PNG\r\n\x1a\nfirst picture"
_JPEG = b"\xff\xd8\xffsecond picture"
_QTI = f"{{{QTI_NAMESPACE}}}"


def _asset(
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


def _round_trip(
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


def _root(
    *,
    identifier: str = "item_001",
    title: str = "Fråga",
    namespace: str = QTI_NAMESPACE,
) -> ElementTree.Element:
    return ElementTree.Element(
        f"{{{namespace}}}qti-assessment-item",
        {"identifier": identifier, "title": title},
    )


def _declaration(
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


def _max_score(root: ElementTree.Element, value: str = "1") -> None:
    outcome = ElementTree.SubElement(
        root,
        f"{_QTI}qti-outcome-declaration",
        {"identifier": "MAXSCORE", "cardinality": "single", "base-type": "float"},
    )
    default_value = ElementTree.SubElement(outcome, f"{_QTI}qti-default-value")
    ElementTree.SubElement(default_value, f"{_QTI}qti-value").text = value


def _body(root: ElementTree.Element) -> ElementTree.Element:
    return ElementTree.SubElement(root, f"{_QTI}qti-item-body")


def _xml(root: ElementTree.Element) -> bytes:
    ElementTree.indent(root, space="  ")
    return ElementTree.tostring(root, encoding="utf-8")


def _read_root(
    root: ElementTree.Element,
    *,
    sequence: int = 1,
    files: dict[str, bytes] | None = None,
) -> tuple[object, ...]:
    return read_examnet_qti_item(
        xml=_xml(root),
        item_path=_ITEM_PATH,
        files=files or {},
        sequence=sequence,
    )


def _unsupported(
    root: ElementTree.Element,
    *,
    reason: ExamNetQtiUnsupportedReason = ExamNetQtiUnsupportedReason.INTERACTION,
    sequence: int = 1,
    files: dict[str, bytes] | None = None,
) -> ExamNetQtiUnsupportedItem:
    (read,) = _read_root(root, sequence=sequence, files=files)
    assert isinstance(read, ExamNetQtiUnsupportedItem)
    assert read.reason is reason
    assert read.sequence == sequence
    return read


def _multiple_response_item() -> NativeExamItem:
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


def _gap_fill_item(*, points: int | float | None, accepted: tuple[str, ...]) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Frastyp: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
        ),
        points=points,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=accepted),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=review_complete(),
    )


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


def test_multiple_response_uses_declaration_cardinality_not_max_choices() -> None:
    item = _multiple_response_item()

    exported, read = _round_trip(item)

    assert exported.interaction_type is ExamNetQtiInteractionType.MULTIPLE_RESPONSE
    assert read.interaction_type is ExamNetQtiInteractionType.MULTIPLE_RESPONSE
    assert read.correct_choice_identifiers == ("choice_001", "choice_003")


@pytest.mark.parametrize("points", [2, None])
def test_gap_fill_reads_every_accepted_value_with_and_without_points(
    points: int | float | None,
) -> None:
    item = _gap_fill_item(points=points, accepted=("NF", "nf"))

    exported, read = _round_trip(item)

    assert exported.max_score == points
    assert read.max_score == points
    assert read.text_entry_gaps == (
        ExamNetQtiTextEntryGap(
            response_identifier=exported.text_entry_gaps[0].response_identifier,
            label="",
            accepted_values=("NF", "nf"),
        ),
    )


def test_a_zero_point_item_reads_max_score_none() -> None:
    item = NativeExamItem.model_validate({**dict(make_single_choice_item()), "points": 0})

    exported, read = _round_trip(item)

    assert exported.max_score == 0
    assert read.max_score is None


def test_free_text_reads_a_one_row_mapping_as_its_criterion_points() -> None:
    item = make_free_text_item()

    exported, read = _round_trip(item)

    assert exported.free_text_criterion_points == 4
    assert read.free_text_criterion_points == 4
    assert read.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
    assert read.max_score == 4


def test_free_text_reads_a_three_row_mapping_as_its_first_row() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=plain_body("Bedöm svaret."),
        points=3,
        criteria=(
            NativeExamCriterion(text="Ett korrekt exempel.", points=1),
            NativeExamCriterion(text="En korrekt förklaring.", points=1),
            NativeExamCriterion(text="En rimlig slutsats.", points=1),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )

    exported, read = _round_trip(item)

    assert exported.free_text_criterion_points == 1
    assert read.free_text_criterion_points == 1
    assert read.max_score == 3
    assert read.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC


def test_free_text_without_points_stays_manual_unkeyed() -> None:
    item = NativeExamItem.model_validate({**dict(make_free_text_item()), "points": None})

    exported, read = _round_trip(item)

    assert exported.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
    assert read.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
    assert read.free_text_criterion_points is None
    assert read.max_score is None


def test_png_and_jpeg_prompt_images_round_trip_in_placement_order() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Före ", marks=()),
                    NativeAssetSegment(asset_id=_ASSET_PNG),
                    NativeTextSegment(text=" mellan ", marks=()),
                    NativeAssetSegment(asset_id=_ASSET_JPEG),
                    NativeTextSegment(text=" efter.", marks=()),
                ),
            ),
        ),
        points=2,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )
    image_paths = ("images/forsta.png", "images/andra.jpg")
    files = {
        f"items/{image_paths[0]}": _PNG,
        f"items/{image_paths[1]}": _JPEG,
    }

    exported, read = _round_trip(
        item,
        image_paths=image_paths,
        files=files,
        assets=(
            _asset(_ASSET_PNG, _PNG, "image/png"),
            _asset(_ASSET_JPEG, _JPEG, "image/jpeg"),
        ),
        payloads={_ASSET_PNG: _PNG, _ASSET_JPEG: _JPEG},
    )

    assert read.prompt_paragraphs == exported.prompt_paragraphs
    assert [image.media_type for image in read.image_resources] == [
        "image/png",
        "image/jpeg",
    ]
    assert [image.payload for image in read.image_resources] == [_PNG, _JPEG]
    assert [image.alt_text for image in read.image_resources] == [
        image.alt_text for image in exported.image_resources
    ]
    assert [image.filename for image in read.image_resources] == [
        "forsta.png",
        "andra.jpg",
    ]


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


def test_mixed_text_entry_and_inline_choice_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="TEXT")
    _declaration(root, identifier="INLINE", base_type="identifier", correct=("choice_001",))
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    ElementTree.SubElement(
        paragraph, f"{_QTI}qti-text-entry-interaction", {"response-identifier": "TEXT"}
    )
    inline = ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-inline-choice-interaction",
        {"response-identifier": "INLINE"},
    )
    ElementTree.SubElement(inline, f"{_QTI}qti-inline-choice", {"identifier": "choice_001"})

    _unsupported(root)


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


def test_inline_choice_without_a_correct_value_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="INLINE", base_type="identifier")
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    inline = ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-inline-choice-interaction",
        {"response-identifier": "INLINE"},
    )
    ElementTree.SubElement(inline, f"{_QTI}qti-inline-choice", {"identifier": "choice_001"})

    _unsupported(root)


def test_inline_choice_with_a_correct_value_outside_its_options_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="INLINE", base_type="identifier", correct=("choice_404",))
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    inline = ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-inline-choice-interaction",
        {"response-identifier": "INLINE"},
    )
    ElementTree.SubElement(inline, f"{_QTI}qti-inline-choice", {"identifier": "choice_001"})

    _unsupported(root)


def test_a_response_identifier_without_a_declaration_is_unsupported() -> None:
    root = _root()
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-text-entry-interaction",
        {"response-identifier": "MISSING"},
    )

    _unsupported(root)


def test_two_choice_interactions_are_left_for_the_parent_unit() -> None:
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

    unsupported = _unsupported(root, sequence=4)

    assert unsupported.sequence == 4
    assert unsupported.opening_text == "Ett alternativ Ett alternativ"


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


def test_an_empty_gap_match_separator_is_left_for_the_parent_unit() -> None:
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
    assert [item.interaction_type for item in read] == [
        ExamNetQtiInteractionType.FREE_TEXT,
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.GAP_FILL,
    ]
    assert [item.max_score for item in read] == [5, 2, 2, 2, 4, 6, 3]
