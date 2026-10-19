"""QTI import mapping: pictures, assets, and document/package shape.

Split from test_qti_import_mapping.py by tested responsibility. Covers stem
and child pictures, repeated payload deduplication, document metadata/origin,
and the read package contracts.
"""

import hashlib
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageItemSource,
    ExamNetQtiPackageSource,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from tests.unit.application.curated_apps.qti_round_trip_support import (
    _body_projection,
    _document_projection,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_review,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.qti_import_mapping_support import (
    _ASSET_ONE,
    _ASSET_TWO,
    _SOURCE_SHA,
    PNG_ONE,
    PNG_TWO,
    _asset,
    _at,
    _document,
    _export_projection,
    _round_trip,
)


def test_two_child_parent_keeps_the_stem_picture_and_each_childs_picture() -> None:
    payloads = {_ASSET_ONE: PNG_ONE, _ASSET_TWO: PNG_TWO}
    pictured_child = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Före ", marks=()),
                    NativeAssetSegment(asset_id=_ASSET_TWO),
                    NativeTextSegment(text=" efter.", marks=()),
                ),
            ),
        ),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
            NativeChoice(choice_id="choice_002", body=plain_body("Två")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_002",),
        ),
        review=make_review(),
    )
    parent = NativeExamParent(
        parent_id="parent_001",
        place=pictured_child.sequence - 1,
        instruction=(
            NativeParagraph(
                heading_level=2,
                segments=(
                    NativeTextSegment(text="Läs texten ", marks=("italic",)),
                    NativeAssetSegment(asset_id=_ASSET_ONE),
                ),
            ),
        ),
        item_ids=("item_001", "item_002"),
    )
    document = _document(
        (pictured_child, _at(make_single_choice_item(), 2)),
        assets=(_asset(_ASSET_ONE, PNG_ONE), _asset(_ASSET_TWO, PNG_TWO)),
        parents=(parent,),
    )

    first_items, container = _round_trip(document, payloads)
    imported = container.document
    sha_by_asset_id = {asset.asset_id: asset.sha256 for asset in imported.assets}

    assert _document_projection(imported) == _document_projection(document)
    assert imported.parents[0].item_ids == ("item_001", "item_002")
    assert _body_projection(imported.parents[0].instruction, sha_by_asset_id)[0][1][1] == (
        "asset",
        hashlib.sha256(PNG_ONE).hexdigest(),
    )
    assert (
        "asset",
        hashlib.sha256(PNG_TWO).hexdigest(),
    ) in _body_projection(imported.items[0].body, sha_by_asset_id)[0][1]
    assert set(container.assets_by_id.values()) == {PNG_ONE, PNG_TWO}
    second_items = native_exam_to_examnet_qti_items(imported, assets_by_id=container.assets_by_id)
    assert _export_projection(second_items) == _export_projection(first_items)
    (parent_qti,) = second_items
    assert len(parent_qti.image_resources) == 2
    assert [len(child.image_resources) for child in parent_qti.children] == [1, 0]


def test_repeated_picture_payloads_become_one_asset() -> None:
    first = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(NativeAssetSegment(asset_id=_ASSET_ONE),),
            ),
        ),
        points=1,
        writing_lines=DEFAULT_WRITING_LINES,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )
    second = NativeExamItem.model_validate(
        {
            **dict(first),
            "item_id": "item_002",
            "sequence": 2,
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(NativeAssetSegment(asset_id=_ASSET_TWO),),
                ),
            ),
        }
    )
    document = _document(
        (first, second),
        assets=(_asset(_ASSET_ONE, PNG_ONE), _asset(_ASSET_TWO, PNG_ONE)),
    )

    _, container = _round_trip(document, {_ASSET_ONE: PNG_ONE, _ASSET_TWO: PNG_ONE})

    assert len(container.document.assets) == 1
    assert list(container.assets_by_id.values()) == [PNG_ONE]


def test_document_metadata_is_revision_one_with_the_qti_import_origin() -> None:
    document_id = uuid4()
    course = ExamCourseChoice(key="matematik", name="Matematik")
    (item,) = native_exam_to_examnet_qti_items(_document((make_free_text_item(),)))

    container = build_native_exam_from_qti(
        items=(item,),
        document_id=document_id,
        source_filename="omprov-i-matematik.qti.zip",
        source_sha256=_SOURCE_SHA,
        course=course,
    )

    document = container.document
    assert document.document_id == document_id
    assert document.revision == 1
    assert document.title == "omprov-i-matematik.qti"
    assert document.header.course == course
    assert document.origin.kind == "qti_import"
    assert document.origin.source_filename == "omprov-i-matematik.qti.zip"
    assert document.origin.source_sha256 == _SOURCE_SHA


def test_the_read_contracts_keep_package_items_in_test_order() -> None:
    item_source = ExamNetQtiPackageItemSource(path="items/item_001.xml", xml=b"<item/>")
    package = ExamNetQtiPackageSource(
        items=(item_source,),
        files={"items/item_001.xml": b"<item/>", "assessment.xml": b"<test/>"},
    )

    assert package.items == (item_source,)
    assert package.files["assessment.xml"] == b"<test/>"
    assert isinstance(package.files, dict)
