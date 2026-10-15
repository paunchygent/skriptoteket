"""Focused tests for the TASK-SKRIPT-39-09-02 QTI scoring decisions.

Purpose:
    Prove the decided scoring shapes on the QTI serializer: an exact equal
    share maps every correct answer, an uneven share exports standalone
    all-or-nothing through custom SCORE response processing with MAXSCORE, a
    parent scores an unmapped child all-or-nothing while still summing its
    mapped children, and one Lucktext gives every gap the same value rounded
    down to 2 decimals.

Relationships:
    - Exercises `domain.examnet_qti_item_xml` with
      `domain.examnet_qti_contracts` value objects.
"""

from __future__ import annotations

from dataclasses import replace
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    MAP_RESPONSE_TEMPLATE,
    QTI_NAMESPACE,
)

pytestmark = pytest.mark.unit


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _root(item: ExamNetQtiItem) -> ElementTree.Element:
    return ElementTree.fromstring(serialize_qti_assessment_item(item))


def _child(parent: ElementTree.Element, local_name: str) -> ElementTree.Element:
    child = parent.find(_tag(local_name))
    assert child is not None
    return child


def _declaration(root: ElementTree.Element, identifier: str) -> ElementTree.Element:
    declaration = root.find(f".//{_tag('qti-response-declaration')}[@identifier='{identifier}']")
    assert declaration is not None
    return declaration


def _max_score_value(root: ElementTree.Element) -> str:
    value = root.find(
        f".//{_tag('qti-outcome-declaration')}[@identifier='MAXSCORE']"
        f"/{_tag('qti-default-value')}/{_tag('qti-value')}"
    )
    assert value is not None
    return value.text or ""


def _choice_item(
    *,
    item_id: str,
    interaction_type: ExamNetQtiInteractionType,
    max_score: int | float,
    correct_count: int,
    choice_count: int = 4,
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=item_id,
        sequence=1,
        title="Flervalsfråga",
        interaction_type=interaction_type,
        prompt_lines=("Välj rätt svar.",),
        max_score=max_score,
        choices=tuple(
            ExamNetQtiChoice(f"choice_{index:03d}", f"Svarsalternativ {index}")
            for index in range(1, choice_count + 1)
        ),
        correct_choice_identifiers=tuple(
            f"choice_{index:03d}" for index in range(1, correct_count + 1)
        ),
    )


def _gap_item(
    *,
    max_score: int | float,
    gap_count: int,
    accepted_values: tuple[str, ...],
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Fyll i luckorna.",),
        max_score=max_score,
        text_entry_gaps=tuple(
            ExamNetQtiTextEntryGap(
                response_identifier=f"RESPONSE_gap_{index:03d}",
                label=f"Lucka {index}",
                accepted_values=accepted_values,
            )
            for index in range(1, gap_count + 1)
        ),
    )


@pytest.mark.parametrize(
    ("max_score", "correct_count", "expected_share"),
    ((1, 4, "0.25"), (2, 2, "1"), (1.5, 3, "0.5"), (0, 3, "0")),
)
def test_exact_equal_share_maps_every_correct_answer(
    max_score: int | float, correct_count: int, expected_share: str
) -> None:
    root = _root(
        _choice_item(
            item_id="item_001",
            interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
            max_score=max_score,
            correct_count=correct_count,
        )
    )
    declaration = _declaration(root, "RESPONSE")

    mapping = declaration.find(_tag("qti-mapping"))
    assert mapping is not None
    assert mapping.attrib == {
        "default-value": "0",
        "lower-bound": "0",
        "upper-bound": str(max_score),
    }
    assert [
        (entry.attrib["map-key"], entry.attrib["mapped-value"])
        for entry in mapping.findall(_tag("qti-map-entry"))
    ] == [(f"choice_{index:03d}", expected_share) for index in range(1, correct_count + 1)]
    assert _max_score_value(root) == str(max_score)
    processing = _child(root, "qti-response-processing")
    assert processing.attrib == {"template": MAP_RESPONSE_TEMPLATE}


@pytest.mark.parametrize(
    ("max_score", "pair_count", "expected_share"),
    ((6, 4, "1.5"), (1, 3, None), (2, 3, None)),
)
def test_matching_uses_equal_maps_or_all_or_nothing(
    max_score: int, pair_count: int, expected_share: str | None
) -> None:
    item = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Matcha ihop",
        interaction_type=ExamNetQtiInteractionType.MATCHING,
        prompt_lines=("Para ihop varje begrepp med rätt förklaring.",),
        max_score=max_score,
        match_pairs=(
            ExamNetQtiMatchPair("left_001", "kloroplast", "right_001", "fotosyntes"),
            ExamNetQtiMatchPair("left_002", "mitokondrie", "right_002", "ATP-produktion"),
            ExamNetQtiMatchPair("left_003", "ribosom", "right_003", "proteinsyntes"),
            ExamNetQtiMatchPair("left_004", "cellkärna", "right_004", "genetisk information"),
        ),
        match_left=(
            ExamNetQtiMatchEntry("left_001", "kloroplast"),
            ExamNetQtiMatchEntry("left_002", "mitokondrie"),
            ExamNetQtiMatchEntry("left_003", "ribosom"),
            ExamNetQtiMatchEntry("left_004", "cellkärna"),
        ),
        match_right=(
            ExamNetQtiMatchEntry("right_001", "fotosyntes"),
            ExamNetQtiMatchEntry("right_002", "ATP-produktion"),
            ExamNetQtiMatchEntry("right_003", "proteinsyntes"),
            ExamNetQtiMatchEntry("right_004", "genetisk information"),
        ),
    )

    item = replace(
        item,
        match_pairs=item.match_pairs[:pair_count],
        match_left=item.match_left[:pair_count],
        match_right=item.match_right[:pair_count],
    )
    root = _root(item)
    declaration = _declaration(root, "RESPONSE")
    assert len(_child(declaration, "qti-correct-response")) == pair_count
    assert _max_score_value(root) == str(max_score)
    mapping = declaration.find(_tag("qti-mapping"))
    processing = _child(root, "qti-response-processing")
    if expected_share is None:
        assert mapping is None
        assert "template" not in processing.attrib
        response_if = _child(_child(processing, "qti-response-condition"), "qti-response-if")
        assert _child(_child(response_if, "qti-match"), "qti-correct").attrib == {
            "identifier": "RESPONSE"
        }
        points = _child(_child(response_if, "qti-set-outcome-value"), "qti-sum")
        assert _child(points, "qti-base-value").text == str(max_score)
    else:
        assert mapping is not None
        assert mapping.attrib["upper-bound"] == str(max_score)
        assert [
            entry.attrib["mapped-value"] for entry in mapping.findall(_tag("qti-map-entry"))
        ] == [expected_share] * pair_count
        assert processing.attrib == {"template": MAP_RESPONSE_TEMPLATE}


@pytest.mark.parametrize(("max_score", "correct_count"), ((1, 3), (2, 3)))
def test_uneven_share_is_standalone_all_or_nothing(max_score: int, correct_count: int) -> None:
    root = _root(
        _choice_item(
            item_id="item_001",
            interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
            max_score=max_score,
            correct_count=correct_count,
        )
    )
    declaration = _declaration(root, "RESPONSE")

    assert declaration.find(_tag("qti-mapping")) is None
    correct_response = _child(declaration, "qti-correct-response")
    assert [value.text for value in correct_response.findall(_tag("qti-value"))] == [
        f"choice_{index:03d}" for index in range(1, correct_count + 1)
    ]
    assert _max_score_value(root) == str(max_score)
    processing = _child(root, "qti-response-processing")
    assert "template" not in processing.attrib

    initial = _child(processing, "qti-set-outcome-value")
    assert initial.attrib["identifier"] == "SCORE"
    initial_value = _child(initial, "qti-base-value")
    assert initial_value.attrib["base-type"] == "float"
    assert initial_value.text == "0"

    condition = _child(processing, "qti-response-condition")
    response_if = _child(condition, "qti-response-if")
    match = _child(response_if, "qti-match")
    assert _child(match, "qti-variable").attrib["identifier"] == "RESPONSE"
    assert _child(match, "qti-correct").attrib["identifier"] == "RESPONSE"
    addition = _child(response_if, "qti-set-outcome-value")
    assert addition.attrib["identifier"] == "SCORE"
    addition_sum = _child(addition, "qti-sum")
    assert _child(addition_sum, "qti-variable").attrib["identifier"] == "SCORE"
    points = _child(addition_sum, "qti-base-value")
    assert points.attrib["base-type"] == "float"
    assert points.text == str(max_score)


def test_parent_scores_unmapped_child_all_or_nothing_and_sums_mapped_children() -> None:
    mapped_child = _choice_item(
        item_id="item_010",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        max_score=1,
        correct_count=1,
    )
    unmapped_child = _choice_item(
        item_id="item_020",
        interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        max_score=2,
        correct_count=3,
    )
    parent = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Delad instruktion",
        interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        prompt_lines=("Läs instruktionen.",),
        max_score=3,
        instruction_lines=("Läs instruktionen.",),
        children=(mapped_child, unmapped_child),
    )

    root = _root(parent)

    mapped_declaration = _declaration(root, "item_010_RESPONSE")
    assert mapped_declaration.find(_tag("qti-mapping")) is not None
    unmapped_declaration = _declaration(root, "item_020_RESPONSE")
    assert unmapped_declaration.find(_tag("qti-mapping")) is None
    assert unmapped_declaration.find(_tag("qti-correct-response")) is not None
    assert _max_score_value(root) == "3"

    processing = _child(root, "qti-response-processing")
    assert "template" not in processing.attrib

    initial = _child(processing, "qti-set-outcome-value")
    assert initial.attrib["identifier"] == "SCORE"
    assert _child(initial, "qti-base-value").text == "0"
    conditions = processing.findall(_tag("qti-response-condition"))
    assert len(conditions) == 2
    mapped_if = _child(conditions[0], "qti-response-if")
    not_null = _child(_child(mapped_if, "qti-not"), "qti-is-null")
    assert _child(not_null, "qti-variable").attrib == {"identifier": "item_010_RESPONSE"}
    mapped_addition = _child(_child(mapped_if, "qti-set-outcome-value"), "qti-sum")
    assert _child(mapped_addition, "qti-variable").attrib == {"identifier": "SCORE"}
    assert _child(mapped_addition, "qti-map-response").attrib == {"identifier": "item_010_RESPONSE"}

    response_if = _child(conditions[1], "qti-response-if")
    match = _child(response_if, "qti-match")
    assert _child(match, "qti-variable").attrib["identifier"] == "item_020_RESPONSE"
    assert _child(match, "qti-correct").attrib["identifier"] == "item_020_RESPONSE"

    addition = _child(response_if, "qti-set-outcome-value")
    assert addition.attrib["identifier"] == "SCORE"
    addition_sum = _child(addition, "qti-sum")
    assert _child(addition_sum, "qti-variable").attrib["identifier"] == "SCORE"
    points = _child(addition_sum, "qti-base-value")
    assert points.attrib["base-type"] == "float"
    assert points.text == "2"


def test_parent_with_only_all_or_nothing_children_starts_at_zero_and_adds_each_score() -> None:
    first = _choice_item(
        item_id="item_010",
        interaction_type=ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        max_score=1,
        correct_count=3,
    )
    second = replace(first, item_id="item_020", max_score=2)
    parent = replace(
        first,
        item_id="parent",
        max_score=3,
        instruction_lines=("Gemensam instruktion.",),
        children=(first, second),
    )

    root = _root(parent)

    assert root.findall(f".//{_tag('qti-mapping')}") == []
    processing = _child(root, "qti-response-processing")
    assert processing.findall(f".//{_tag('qti-map-response')}") == []
    initial = _child(processing, "qti-set-outcome-value")
    assert _child(initial, "qti-base-value").text == "0"
    conditions = processing.findall(_tag("qti-response-condition"))
    assert len(conditions) == 2
    for condition, response_id, points in zip(
        conditions, ("item_010_RESPONSE", "item_020_RESPONSE"), ("1", "2"), strict=True
    ):
        response_if = _child(condition, "qti-response-if")
        match = _child(response_if, "qti-match")
        assert _child(match, "qti-variable").attrib == {"identifier": response_id}
        assert _child(match, "qti-correct").attrib == {"identifier": response_id}
        addition = _child(_child(response_if, "qti-set-outcome-value"), "qti-sum")
        assert _child(addition, "qti-variable").attrib == {"identifier": "SCORE"}
        assert _child(addition, "qti-base-value").text == points


@pytest.mark.parametrize(
    ("max_score", "expected_value"),
    ((1, "0.33"), (2, "0.66"), (3, "1"), (4.5, "1.5")),
)
def test_lucktext_gives_every_gap_the_same_rounded_down_value(
    max_score: int | float, expected_value: str
) -> None:
    root = _root(_gap_item(max_score=max_score, gap_count=3, accepted_values=("svar",)))

    declarations = root.findall(_tag("qti-response-declaration"))
    assert len(declarations) == 3
    for index, declaration in enumerate(declarations, start=1):
        assert declaration.attrib["identifier"] == f"RESPONSE_gap_{index:03d}"
        mapping = declaration.find(_tag("qti-mapping"))
        assert mapping is not None
        assert mapping.attrib == {
            "default-value": "0",
            "lower-bound": "0",
            "upper-bound": expected_value,
        }
        assert [
            entry.attrib["mapped-value"] for entry in mapping.findall(_tag("qti-map-entry"))
        ] == [expected_value]
    assert _max_score_value(root) == str(max_score)


def test_lucktext_value_rounded_to_zero_keeps_accepted_values_without_mapping() -> None:
    root = _root(_gap_item(max_score=0.02, gap_count=3, accepted_values=("alfa", "Alfa")))

    declarations = root.findall(_tag("qti-response-declaration"))
    assert len(declarations) == 3
    for declaration in declarations:
        assert declaration.find(_tag("qti-mapping")) is None
        correct_response = _child(declaration, "qti-correct-response")
        assert [value.text for value in correct_response.findall(_tag("qti-value"))] == [
            "alfa",
            "Alfa",
        ]
    assert _max_score_value(root) == "0.02"


def test_zero_point_lucktext_keeps_accepted_values_without_mapping() -> None:
    root = _root(_gap_item(max_score=0, gap_count=3, accepted_values=("beta",)))

    declarations = root.findall(_tag("qti-response-declaration"))
    assert len(declarations) == 3
    for declaration in declarations:
        assert declaration.find(_tag("qti-mapping")) is None
        correct_response = _child(declaration, "qti-correct-response")
        assert [value.text for value in correct_response.findall(_tag("qti-value"))] == ["beta"]
    assert _max_score_value(root) == "0"
