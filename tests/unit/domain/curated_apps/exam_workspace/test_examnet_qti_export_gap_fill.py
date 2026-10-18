"""Mapping tests for gap-fill items in the native exam -> Exam.net QTI adapter."""

import hashlib
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
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
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    ASSET_ID,
    ASSET_PAYLOAD,
    document_of,
    review_complete,
    text_body,
)


class TestGapFillMapping:
    @pytest.mark.parametrize("shared_parent", [False, True])
    def test_rich_prompt_reordered_gaps_bind_the_answers_at_their_placed_blanks(
        self,
        shared_parent: bool,
    ) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Beta: ", marks=()),
                        NativeGapSegment(gap_id="gap_002"),
                        NativeAssetSegment(asset_id=ASSET_ID),
                        NativeTextSegment(text="Alpha: ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
                ),
            ),
            points=2,
            gaps=(
                NativeGap(gap_id="gap_001", accepted_values=("alpha",)),
                NativeGap(gap_id="gap_002", accepted_values=("beta",)),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=review_complete(),
        )
        asset = NativeExamAsset(
            asset_id=ASSET_ID,
            media_type="image/png",
            byte_length=len(ASSET_PAYLOAD),
            sha256=hashlib.sha256(ASSET_PAYLOAD).hexdigest(),
        )
        document = document_of((item,), (asset,))
        if shared_parent:
            document = document.model_copy(
                update={
                    "parents": (
                        NativeExamParent(
                            parent_id="parent_001",
                            place=item.sequence - 1,
                            instruction=text_body("Gemensam instruktion."),
                            item_ids=(item.item_id,),
                        ),
                    )
                }
            )
        (qti_item,) = native_exam_to_examnet_qti_items(
            document,
            assets_by_id={ASSET_ID: ASSET_PAYLOAD},
        )
        root = ElementTree.fromstring(
            serialize_qti_assessment_item(qti_item, image_paths=("../images/diagram.png",)),
        )
        placed = tuple(
            element.attrib["response-identifier"]
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-text-entry-interaction"
        )
        prefix = "item_001_" if shared_parent else ""
        assert placed == (f"{prefix}RESPONSE_gap_002", f"{prefix}RESPONSE_gap_001")
        declarations = {
            element.attrib["identifier"]: tuple(
                child.text
                for child in element.iter()
                if child.tag.rsplit("}", 1)[-1] == "qti-value"
            )
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-response-declaration"
        }
        assert declarations[placed[0]] == ("beta",)
        assert declarations[placed[1]] == ("alpha",)

    def test_gaps_follow_body_placement_order_with_native_gap_ids(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="a) Först: ", marks=()),
                        NativeGapSegment(gap_id="gap_002"),
                    ),
                ),
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="b) Sedan: ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
                ),
            ),
            points=2,
            gaps=(
                NativeGap(gap_id="gap_001", accepted_values=("NF",)),
                NativeGap(gap_id="gap_002", accepted_values=("VF", "verbfras")),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.GAP_FILL
        assert qti_item.prompt_lines == ("a) Först: [___]", "b) Sedan: [___]")
        assert tuple(gap.response_identifier for gap in qti_item.text_entry_gaps) == (
            "RESPONSE_gap_002",
            "RESPONSE_gap_001",
        )
        assert tuple(gap.label for gap in qti_item.text_entry_gaps) == ("Lucka 1", "Lucka 2")
        assert qti_item.text_entry_gaps[0].accepted_values == ("VF", "verbfras")
        assert qti_item.text_entry_gaps[1].accepted_values == ("NF",)

    def test_automatic_values_join_the_gaps_accepted_answers_after_them(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Ange frastyp: ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
                ),
            ),
            points=2,
            gaps=(
                NativeGap(
                    gap_id="gap_001",
                    accepted_values=("nominalfras",),
                    automatic_values=("nominalfas", "nomminalfras"),
                ),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.AI_INTERPRETED),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.text_entry_gaps[0].accepted_values == (
            "nominalfras",
            "nominalfas",
            "nomminalfras",
        )

    def test_gap_without_points_writes_every_accepted_value_in_the_correct_response(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Ange frastyp: ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
                ),
            ),
            gaps=(
                NativeGap(
                    gap_id="gap_001",
                    accepted_values=("nominalfras",),
                    automatic_values=("nominalfas",),
                ),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.max_score is None
        root = ElementTree.fromstring(serialize_qti_assessment_item(qti_item))
        correct_values = tuple(
            child.text
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-correct-response"
            for child in element
            if child.tag.rsplit("}", 1)[-1] == "qti-value"
        )
        assert correct_values == ("nominalfras", "nominalfas")
        assert [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "qti-mapping"] == []
