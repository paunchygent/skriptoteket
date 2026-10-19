"""Dropdown export proof: XML keys, placement, points and parent separators."""

from decimal import Decimal
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import qti_tag
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    ExamNetExportChecklistRoundedGaps,
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body


def _saved_document(*, parented: bool, points: float | None) -> NativeExamDocument:
    items: tuple[NativeExamItem, ...] = (inline_choice_item(points=points),)
    if parented:
        items += (inline_choice_item(sequence=2, points=points),)
    document = document_of(items)
    if parented:
        document = NativeExamDocument.model_validate(
            {
                **document.model_dump(),
                "parents": (
                    NativeExamParent(
                        parent_id="parent_001",
                        place=items[0].sequence - 1,
                        instruction=plain_body("Välj rätt ord."),
                        item_ids=tuple(item.item_id for item in items),
                    ),
                ),
            }
        )
    return NativeExamDocument.model_validate_json(document.model_dump_json())


@pytest.mark.parametrize("parented", [False, True])
@pytest.mark.parametrize("points,share", [(2.01, Decimal("1")), (0.01, None), (None, None)])
def test_saved_dropdown_xml_binds_each_local_key_and_point_mapping(
    parented: bool, points: float | None, share: Decimal | None
) -> None:
    document = _saved_document(parented=parented, points=points)
    (qti,) = native_exam_to_examnet_qti_items(document)
    root = ElementTree.fromstring(serialize_qti_assessment_item(qti))
    interactions = list(root.iter(qti_tag("qti-inline-choice-interaction")))
    assert len(interactions) == (4 if parented else 2)
    identifiers = [interaction.attrib["response-identifier"] for interaction in interactions]
    assert len(set(identifiers)) == len(identifiers)
    declarations = {
        declaration.attrib["identifier"]: declaration
        for declaration in root.iter(qti_tag("qti-response-declaration"))
    }
    for index, interaction in enumerate(interactions):
        # Placement is Beta then Alfa, not the gaps tuple's Alfa then Beta.
        label, correct_index = ("Beta", 1) if index % 2 == 0 else ("Alfa", 0)
        choices = list(interaction.findall(qti_tag("qti-inline-choice")))
        assert ["".join(choice.itertext()).strip() for choice in choices] == [
            f"{label} {option} & <text>" for option in (1, 2, 3)
        ]
        assert len({choice.attrib["identifier"] for choice in choices}) == 3
        declaration = declarations[interaction.attrib["response-identifier"]]
        assert declaration.attrib["cardinality"] == "single"
        assert declaration.attrib["base-type"] == "identifier"
        correct = declaration.findall(f"{qti_tag('qti-correct-response')}/{qti_tag('qti-value')}")
        assert [value.text for value in correct] == [choices[correct_index].attrib["identifier"]]
        mapping = declaration.find(qti_tag("qti-mapping"))
        if share is None:
            assert mapping is None
        else:
            assert mapping is not None
            assert Decimal(mapping.attrib["default-value"]) == 0
            assert Decimal(mapping.attrib["upper-bound"]) == share
            entries = list(mapping.findall(qti_tag("qti-map-entry")))
            assert len(entries) == 1
            assert entries[0].attrib["map-key"] == correct[0].text
            assert Decimal(entries[0].attrib["mapped-value"]) == share
    assert list(root.iter(qti_tag("qti-text-entry-interaction"))) == []
    body = root.find(qti_tag("qti-item-body"))
    assert body is not None
    text = "".join(body.itertext())
    assert "Beta & <två>:" in text
    assert "; alfa:" in text
    if parented:
        separators = [
            node
            for node in body.iter(qti_tag("qti-gap-match-interaction"))
            if node.attrib["response-identifier"].endswith("_SEPARATOR")
        ]
        assert len(separators) == 2
        body_order = list(body.iter())
        for child_index, separator in enumerate(separators):
            assert list(separator) == []
            separator_index = body_order.index(separator)
            first_gap_index = body_order.index(interactions[child_index * 2])
            assert separator_index < first_gap_index
            if child_index:
                assert body_order.index(interactions[child_index * 2 - 1]) < separator_index
    else:
        assert list(body.iter(qti_tag("qti-gap-match-interaction"))) == []


@pytest.mark.parametrize("parented", [False, True])
@pytest.mark.parametrize(
    "mark,tag",
    [
        ("superscript", "sup"),
        ("subscript", "sub"),
        ("bold", "strong"),
        ("italic", "em"),
        ("underline", "u"),
    ],
)
def test_dropdown_options_keep_marks_distinct_from_identical_plain_text(
    parented: bool, mark: str, tag: str
) -> None:
    document = _saved_document(parented=parented, points=2.01)
    payload = document.model_dump(mode="json")
    for item in payload["items"]:
        for gap in item["gaps"]:
            gap["options"][0]["body"] = [
                {
                    "heading_level": None,
                    "segments": [
                        {"kind": "text", "text": "x", "marks": []},
                        {"kind": "text", "text": "2", "marks": [mark]},
                        {"kind": "text", "text": " & <tail>", "marks": []},
                    ],
                }
            ]
            gap["options"][1]["body"] = [
                {
                    "heading_level": None,
                    "segments": [
                        {"kind": "text", "text": "x2 & <tail>", "marks": []},
                    ],
                }
            ]
    document = NativeExamDocument.model_validate_json(
        NativeExamDocument.model_validate(payload).model_dump_json()
    )
    (qti,) = native_exam_to_examnet_qti_items(document)
    root = ElementTree.fromstring(serialize_qti_assessment_item(qti))
    interactions = list(root.iter(qti_tag("qti-inline-choice-interaction")))
    assert len(interactions) == (4 if parented else 2)
    for index, interaction in enumerate(interactions):
        formatted, plain, _ = interaction.findall(qti_tag("qti-inline-choice"))
        assert "".join(formatted.itertext()) == "x2 & <tail>"
        assert "".join(plain.itertext()) == "x2 & <tail>"
        assert formatted.text == "x"
        marked = formatted.find(qti_tag(tag))
        assert marked is not None
        assert marked.text == "2"
        assert marked.tail == " & <tail>"
        assert list(plain) == []
        assert [node.tag for node in formatted] == [qti_tag(tag)]
        declaration = next(
            node
            for node in root.iter(qti_tag("qti-response-declaration"))
            if node.attrib["identifier"] == interaction.attrib["response-identifier"]
        )
        key = declaration.find(f"{qti_tag('qti-correct-response')}/{qti_tag('qti-value')}")
        assert key is not None
        expected_key = plain if index % 2 == 0 else formatted
        assert key.text == expected_key.attrib["identifier"]
        mapping = declaration.find(qti_tag("qti-mapping"))
        assert mapping is not None
        assert Decimal(mapping.attrib["upper-bound"]) == 1


def test_dropdown_option_paragraphs_render_only_inline_content() -> None:
    payload = _saved_document(parented=False, points=2).model_dump(mode="json")
    option = payload["items"][0]["gaps"][1]["options"][0]
    option["body"] = [
        {
            "heading_level": None,
            "segments": [
                {"kind": "text", "text": "x\n2", "marks": ["bold", "italic"]},
            ],
        },
        {
            "heading_level": None,
            "segments": [
                {"kind": "text", "text": "tail", "marks": ["underline"]},
            ],
        },
    ]
    document = NativeExamDocument.model_validate(payload)
    (qti,) = native_exam_to_examnet_qti_items(document)
    root = ElementTree.fromstring(serialize_qti_assessment_item(qti))
    choice = next(root.iter(qti_tag("qti-inline-choice")))
    assert [element.tag for element in choice] == [
        qti_tag("strong"),
        qti_tag("br"),
        qti_tag("strong"),
        qti_tag("br"),
        qti_tag("u"),
    ]
    assert [element.text for element in choice.iter(qti_tag("em"))] == ["x", "2"]
    assert "".join("".join(choice.itertext()).split()) == "x2tail"


@pytest.mark.parametrize("heading_level", [1, 2, 3])
def test_dropdown_heading_option_has_named_blocker_and_serializer_defence(
    heading_level: int,
) -> None:
    payload = _saved_document(parented=False, points=2).model_dump(mode="json")
    payload["items"][0]["gaps"][0]["options"][0]["body"][0]["heading_level"] = heading_level
    document = NativeExamDocument.model_validate(payload)
    assert [(blocker.item_id, blocker.reason) for blocker in native_export_blockers(document)] == [
        ("item_001", "inline_choice_option_heading"),
    ]
    (qti,) = native_exam_to_examnet_qti_items(document)
    with pytest.raises(ValueError, match="inline-choice options cannot render heading levels"):
        serialize_qti_assessment_item(qti)


@pytest.mark.parametrize("parented", [False, True])
@pytest.mark.parametrize("points,share", [(2.01, 1), (0.01, 0), (2, None), (None, None)])
def test_dropdown_checklist_reports_only_actual_gap_point_loss(
    parented: bool, points: float | None, share: int | None
) -> None:
    entries = native_exam_export_checklist(_saved_document(parented=parented, points=points))
    if share is None:
        assert entries == ()
        return
    assert len(entries) == (2 if parented else 1)
    assert all(isinstance(entry, ExamNetExportChecklistRoundedGaps) for entry in entries)
    for entry in entries:
        assert isinstance(entry, ExamNetExportChecklistRoundedGaps)
        assert entry.points == points
        assert entry.gap_points == share
