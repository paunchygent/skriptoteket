"""Tests for model-facing DigiExam gap-fill answer-key projection."""

from __future__ import annotations

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    gap_fill_answer_key_model_payload,
    numbered_gap_labels,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)

_GAP_IDS = (
    "84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1",
    "21d786a3-2f14-49f1-8ffc-388f06d9a20c",
)


def _gap_fill_item() -> DigiExamIrItem:
    question: dict[str, JsonValue] = {
        "id": 1,
        "title": "Choose from the word bank",
        "about": "",
        "bodyHTML": (
            "<p>Complete "
            f'<span class="dxWordGap" dx-wg-id="{_GAP_IDS[0]}">{_GAP_IDS[0]}</span>'
            " and "
            f'<span class="dxWordGap" dx-wg-id="{_GAP_IDS[1]}">{_GAP_IDS[1]}</span>'
            " from the word bank: <strong>apple, pear</strong>.</p>"
        ),
        "images": [],
        "maxScore": 1,
        "type": 3,
        "blanks": [{"guid": gap_id, "validations": []} for gap_id in _GAP_IDS],
    }
    parsed = DigiExamDxeParser().parse_payload(
        {"exams": [{"questions": [question]}]},
        filename="synthetic-gap.dxe",
    )
    return build_digiexam_intermediate_exam(parsed).items[0]


def test_gap_projection_replaces_internal_span_content_with_numbered_marker() -> None:
    payload = gap_fill_answer_key_model_payload(_gap_fill_item())

    item_payload = payload["item"]
    assert isinstance(item_payload, dict)
    assert item_payload["cloze_text"] == ("Complete [1] and [2] from the word bank: apple, pear.")


def _two_pair_gap_item() -> DigiExamIrItem:
    question: dict[str, JsonValue] = {
        "id": 2,
        "title": "Taxonomy",
        "about": "",
        "bodyHTML": (
            "<p>Kingdom of mushrooms: "
            f'<span class="dxWordGap" dx-wg-id="{_GAP_IDS[0]}">___</span>'
            "&nbsp;&nbsp;&nbsp; Domain of bacteria: "
            f'<span class="dxWordGap" dx-wg-id="{_GAP_IDS[1]}">___</span></p>'
        ),
        "images": [],
        "maxScore": 1,
        "type": 3,
        "blanks": [{"guid": gap_id, "validations": []} for gap_id in _GAP_IDS],
    }
    parsed = DigiExamDxeParser().parse_payload(
        {"exams": [{"questions": [question]}]},
        filename="synthetic-two-pair-gap.dxe",
    )
    return build_digiexam_intermediate_exam(parsed).items[0]


def test_gap_entries_carry_the_text_printed_before_each_marker() -> None:
    payload = gap_fill_answer_key_model_payload(_two_pair_gap_item())

    item_payload = payload["item"]
    assert isinstance(item_payload, dict)
    assert item_payload["cloze_text"] == "Kingdom of mushrooms: [1] Domain of bacteria: [2]"
    assert payload["gaps"] == [
        {"gap_number": 1, "label": "Kingdom of mushrooms"},
        {"gap_number": 2, "label": "Domain of bacteria"},
    ]


def test_word_bank_gap_entries_label_each_marker_with_its_preceding_words() -> None:
    payload = gap_fill_answer_key_model_payload(_gap_fill_item())

    assert payload["gaps"] == [
        {"gap_number": 1, "label": "Complete"},
        {"gap_number": 2, "label": "and"},
    ]


@pytest.mark.parametrize(
    ("cloze_text", "gap_count", "expected"),
    [
        (
            "Kingdom of mushrooms: [1] Domain of bacteria: [2]",
            2,
            ("Kingdom of mushrooms", "Domain of bacteria"),
        ),
        ("Name: [1]\nAge: [2]", 2, ("Name", "Age")),
        ("[1] [2]", 2, ("", "")),
        ("[1]", 1, ("",)),
        ("Only one: [1]", 2, ("Only one", "")),
        ("Missing first [2]", 2, ("", "Missing first")),
        ("Ratio: [1]:[2]", 2, ("Ratio", "")),
        ("Time:: [1]", 1, ("Time:",)),
        ("Before [1] middle [2] after", 2, ("Before", "middle")),
        ("Line one\nprefix [1] and [3] then [2]", 2, ("prefix", "then")),
        ("Scores [1] and [10]", 1, ("Scores",)),
        ("", 1, ("",)),
        ("Anything [1]", 0, ()),
    ],
)
def test_numbered_gap_labels(cloze_text: str, gap_count: int, expected: tuple[str, ...]) -> None:
    assert numbered_gap_labels(cloze_text, gap_count) == expected
