"""Kept-answer links export to QTI as plain words and never as gaps (TASK-SKRIPT-40-04-13 H1)."""

from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_prompt import (
    prompt_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
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


def kept_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Ange frastyp: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" Ordet ", marks=()),
                    NativeTextSegment(text="nominalfras", marks=("bold",), kept_gap_id="gap_002"),
                    NativeTextSegment(text=" kvar.", marks=()),
                ),
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=("VF",)),),
        kept_gaps=(NativeGap(gap_id="gap_002", accepted_values=("nominalfras", "NF")),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=review_complete(),
    )


class TestQtiKeptGaps:
    def test_prompt_mapping_renders_the_kept_word_as_plain_marked_text(self) -> None:
        (paragraph,) = prompt_paragraphs(kept_item().body, gap_ids=("gap_001",))
        kept = [
            segment
            for segment in paragraph.segments
            if isinstance(segment, ExamNetQtiPromptText) and segment.text == "nominalfras"
        ]

        assert kept == [ExamNetQtiPromptText("nominalfras", ("bold",))]
        assert all(
            not isinstance(segment, ExamNetQtiPromptText) or "gap_002" not in segment.text
            for segment in paragraph.segments
        )

    def test_emitted_item_places_live_gaps_only(self) -> None:
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((kept_item(),)))

        assert qti_item.prompt_lines == ("Ange frastyp: [___] Ordet nominalfras kvar.",)
        assert tuple(gap.response_identifier for gap in qti_item.text_entry_gaps) == (
            "RESPONSE_gap_001",
        )
        assert qti_item.text_entry_gaps[0].accepted_values == ("VF",)

        root = ElementTree.fromstring(serialize_qti_assessment_item(qti_item))
        interactions = [
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-text-entry-interaction"
        ]
        key_values = tuple(
            child.text
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-correct-response"
            for child in element
            if child.tag.rsplit("}", 1)[-1] == "qti-value"
        )
        map_keys = tuple(
            element.attrib["map-key"]
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-map-entry"
        )

        assert len(interactions) == 1
        assert key_values == ("VF",)
        assert map_keys == ("VF",)
        assert "nominalfras" in ElementTree.tostring(root, encoding="unicode")
