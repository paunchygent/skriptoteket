"""Mapping tests for matching-grid items in the native exam -> Exam.net QTI adapter."""

from decimal import Decimal
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
    review_complete,
    text_body,
)


class TestMatchingGridMapping:
    def _grid_item(self, *, tick_points: Decimal, points: float) -> NativeExamItem:
        return NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.MATCHING,
            body=text_body("Sätt varje ord i rätt kategori."),
            points=points,
            tick_points=tick_points,
            match_left=(
                NativeMatchLeft(left_id="left_001", text="Rött"),
                NativeMatchLeft(left_id="left_002", text="Päron"),
            ),
            match_right=(
                NativeMatchRight(right_id="right_001", text="Färg"),
                NativeMatchRight(right_id="right_002", text="Frukt"),
                NativeMatchRight(right_id="right_003", text="Obrukad"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                match_pairs=(
                    NativeMatchPair(left_id="left_001", right_id="right_001"),
                    NativeMatchPair(left_id="left_001", right_id="right_002"),
                    NativeMatchPair(left_id="left_002", right_id="right_002"),
                ),
            ),
            review=review_complete(),
        )

    @pytest.mark.parametrize(
        ("tick_points", "points", "tick"),
        ((Decimal("0.5"), 1.5, "0.5"), (Decimal("0.7"), 2.1, "0.7")),
    )
    def test_grid_sets_row_and_column_match_max_and_maps_every_tick_at_tick_points(
        self, tick_points: Decimal, points: float, tick: str
    ) -> None:
        (qti_item,) = native_exam_to_examnet_qti_items(
            document_of((self._grid_item(tick_points=tick_points, points=points),))
        )

        assert qti_item.interaction_type is ExamNetQtiInteractionType.MATCHING
        assert qti_item.max_score == points
        assert [entry.text for entry in qti_item.match_left] == ["Rött", "Päron"]
        assert [entry.text for entry in qti_item.match_right] == ["Färg", "Frukt", "Obrukad"]

        root = ElementTree.fromstring(serialize_qti_assessment_item(qti_item))
        (interaction,) = [
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-match-interaction"
        ]
        assert interaction.attrib["max-associations"] == "6"
        left_set, right_set = [
            element
            for element in interaction
            if element.tag.rsplit("}", 1)[-1] == "qti-simple-match-set"
        ]
        assert [choice.attrib["match-max"] for choice in left_set] == ["3", "3"]
        assert [choice.attrib["match-max"] for choice in right_set] == ["2", "2", "2"]

        (correct,) = [
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-correct-response"
        ]
        assert [
            element.text for element in correct if element.tag.rsplit("}", 1)[-1] == "qti-value"
        ] == [
            "left_001 right_001",
            "left_001 right_002",
            "left_002 right_002",
        ]
        assert [
            (entry.attrib["map-key"], entry.attrib["mapped-value"])
            for entry in root.iter()
            if entry.tag.rsplit("}", 1)[-1] == "qti-map-entry"
        ] == [
            ("left_001 right_001", tick),
            ("left_001 right_002", tick),
            ("left_002 right_002", tick),
        ]
        outcomes = {
            outcome.attrib["identifier"]: outcome
            for outcome in root.iter()
            if outcome.tag.rsplit("}", 1)[-1] == "qti-outcome-declaration"
        }
        max_value = next(
            element
            for element in outcomes["MAXSCORE"].iter()
            if element.tag.rsplit("}", 1)[-1] == "qti-value"
        )
        assert max_value.text == str(points)

        local_names = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
        assert "qti-associate-interaction" not in local_names
        assert "qti-order-interaction" not in local_names
