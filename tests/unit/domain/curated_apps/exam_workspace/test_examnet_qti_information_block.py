"""A childless part's printed instruction exports as an unnumbered information block (G5).

The part holds no question, so its QTI item carries the shared stem as a plain
``qti-item-body`` and nothing else: no response declaration, no outcome declaration, no
response processing and no interaction. Exam.net imports it as an information block.
"""

import hashlib
import io
import posixpath
import zipfile
from uuid import uuid4
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_review,
    plain_body,
)

_ASSET_ID = "asset_0123456789abcdef"
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108040000"
    "00b51c0c020000000b4944415478da636ffcff1f0003030200efbfa7db0000000049454e44ae426082"
)

_INTERACTION_TAGS = (
    "qti-choice-interaction",
    "qti-match-interaction",
    "qti-order-interaction",
    "qti-extended-text-interaction",
    "qti-gap-match-interaction",
    "qti-text-entry-interaction",
    "qti-inline-choice-interaction",
)
_FORBIDDEN_ITEM_TAGS = (
    "qti-response-declaration",
    "qti-outcome-declaration",
    "qti-response-processing",
    "qti-rubric-block",
)


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _root(item: ExamNetQtiItem, image_paths: tuple[str, ...] = ()) -> ElementTree.Element:
    return ElementTree.fromstring(serialize_qti_assessment_item(item, image_paths=image_paths))


def _text(value: str) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=value, marks=()),))


def _free_text(
    sequence: int,
    *,
    item_id: str,
    points: int = 2,
    criteria: tuple[NativeExamCriterion, ...] = (),
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=plain_body("Resonera om texten."),
        points=points,
        criteria=criteria,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )


def _part(
    parent_id: str,
    place: int,
    instruction: tuple[NativeParagraph, ...],
    item_ids: tuple[str, ...] = (),
) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        place=place,
        instruction=instruction,
        item_ids=item_ids,
    )


def _document(
    *,
    items: tuple[NativeExamItem, ...],
    parents: tuple[NativeExamParent, ...] = (),
    assets: tuple[NativeExamAsset, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov på svenska",
        items=items,
        parents=parents,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _information(items: tuple[ExamNetQtiItem, ...]) -> ExamNetQtiItem:
    (information,) = (
        item for item in items if item.interaction_type is ExamNetQtiInteractionType.INFORMATION
    )
    return information


def _assert_no_interaction_or_scoring(root: ElementTree.Element) -> None:
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        assert not local_name.endswith("-interaction"), local_name
        assert local_name not in _FORBIDDEN_ITEM_TAGS, local_name


def _package(
    items: tuple[ExamNetQtiItem, ...],
) -> tuple[ExamNetQtiPackageStatus, zipfile.ZipFile]:
    plan = build_examnet_qti_package_plan(package_name="exam", assessment_title="Prov", items=items)
    assert plan.status is ExamNetQtiPackageStatus.PASSED, plan.warnings
    package = ExamNetQtiPackageWriter().build_package_bytes(plan)
    report = build_examnet_qti_validation_report(
        plan=plan, package_filename="exam.zip", package_bytes=package
    )
    return report.package_status, zipfile.ZipFile(io.BytesIO(package))


class TestInformationBlock:
    def test_a_childless_printed_part_exports_one_information_item_in_place(self) -> None:
        document = _document(
            items=(
                _free_text(1, item_id="item_001"),
                _free_text(2, item_id="item_002"),
            ),
            parents=(_part("parent_001", 1, (_text("Läs igenom texten först."),)),),
        )

        items = native_exam_to_examnet_qti_items(document)

        assert [item.item_id for item in items] == ["item_001", "parent_001", "item_002"]
        information = _information(items)
        assert information.sequence == 1
        assert information.max_score is None
        assert information.title == "Instruktion"

        root = _root(information)
        assert root.attrib["identifier"] == "parent_001"
        body = root.find(_tag("qti-item-body"))
        assert body is not None
        assert "Läs igenom texten först." in "".join(body.itertext())
        _assert_no_interaction_or_scoring(root)

    def test_the_packaged_information_block_keeps_its_place_and_is_not_blocked(self) -> None:
        document = _document(
            items=(
                _free_text(1, item_id="item_001"),
                _free_text(2, item_id="item_002"),
            ),
            parents=(_part("parent_001", 1, (_text("Läs igenom texten först."),)),),
        )
        items = native_exam_to_examnet_qti_items(document)
        plan = build_examnet_qti_package_plan(
            package_name="exam", assessment_title="Prov", items=items
        )

        assert plan.status is ExamNetQtiPackageStatus.PASSED
        assert plan.warnings == ()
        assert not any(follow_up.item_id == "parent_001" for follow_up in plan.manual_follow_ups)

        status, archive = _package(items)
        assert status is ExamNetQtiPackageStatus.PASSED
        refs = [
            ref.attrib["href"]
            for ref in ElementTree.fromstring(archive.read(EXAMNET_QTI_ASSESSMENT_TEST_PATH)).iter(
                _tag("qti-assessment-item-ref")
            )
        ]
        assert refs == ["items/item_001.xml", "items/parent_001.xml", "items/item_002.xml"]

    def test_a_childless_part_with_an_empty_instruction_exports_nothing(self) -> None:
        document = _document(
            items=(
                _free_text(1, item_id="item_001"),
                _free_text(2, item_id="item_002"),
            ),
            parents=(_part("parent_001", 1, ()),),
        )

        items = native_exam_to_examnet_qti_items(document)

        assert [item.item_id for item in items] == ["item_001", "item_002"]

    def test_childless_parts_at_the_start_and_the_end_keep_their_places(self) -> None:
        document = _document(
            items=(
                _free_text(1, item_id="item_001"),
                _free_text(2, item_id="item_002"),
            ),
            parents=(
                _part("parent_001", 0, (_text("Före alla frågor."),)),
                _part("parent_002", 2, (_text("Efter alla frågor."),)),
            ),
        )

        items = native_exam_to_examnet_qti_items(document)

        assert [item.item_id for item in items] == [
            "parent_001",
            "item_001",
            "item_002",
            "parent_002",
        ]
        assert items[0].sequence == 0
        assert items[-1].sequence == 2

    def test_a_picture_in_the_instruction_is_one_image_resource_of_the_information_item(
        self,
    ) -> None:
        document = _document(
            items=(_free_text(1, item_id="item_001"),),
            parents=(
                _part(
                    "parent_001",
                    1,
                    (
                        _text("Studera bilden."),
                        NativeParagraph(
                            heading_level=None,
                            segments=(NativeAssetSegment(asset_id=_ASSET_ID),),
                        ),
                    ),
                ),
            ),
            assets=(
                NativeExamAsset(
                    asset_id=_ASSET_ID,
                    sha256=hashlib.sha256(_PNG).hexdigest(),
                    media_type="image/png",
                    byte_length=len(_PNG),
                ),
            ),
        )

        items = native_exam_to_examnet_qti_items(document, assets_by_id={_ASSET_ID: _PNG})
        information = _information(items)

        assert len(information.image_resources) == 1
        assert information.image_resources[0].source_reference == _ASSET_ID

        plan = build_examnet_qti_package_plan(
            package_name="exam", assessment_title="Prov", items=items
        )
        image_files = [
            file for file in plan.files if file.relative_path.startswith("items/images/")
        ]
        assert len(image_files) == 1

        image_path = posixpath.relpath(image_files[0].relative_path, "items")
        root = _root(information, (image_path,))
        images = list(root.iter(_tag("img")))
        assert len(images) == 1
        assert images[0].attrib["src"] == image_path

    def test_the_export_checklist_has_no_entry_for_an_information_block(self) -> None:
        document = _document(
            items=(
                _free_text(
                    1,
                    item_id="item_001",
                    points=3,
                    criteria=(NativeExamCriterion(text="Ett korrekt exempel.", points=3),),
                ),
                _free_text(2, item_id="item_002"),
            ),
            parents=(_part("parent_001", 1, (_text("Läs igenom texten först."),)),),
        )

        with_block = native_exam_export_checklist(document)
        without_block = native_exam_export_checklist(_document(items=document.items))

        assert with_block == without_block
        assert [entry.question_number for entry in with_block] == ["1"]

        # A block at place 0 names no native question, so the checklist must skip it
        # rather than look one up by its sequence.
        leading = _document(
            items=(
                _free_text(1, item_id="item_001"),
                _free_text(2, item_id="item_002"),
            ),
            parents=(_part("parent_001", 0, (_text("Före alla frågor."),)),),
        )
        assert native_exam_export_checklist(leading) == ()
