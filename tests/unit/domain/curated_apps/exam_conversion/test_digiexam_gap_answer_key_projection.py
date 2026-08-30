"""Tests for model-facing DigiExam gap-fill answer-key projection."""

from __future__ import annotations

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    manual_answer_key_from_model_content,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    gap_fill_answer_key_model_payload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamOverlayGapFillManualAnswerKey,
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


def test_gap_proposal_rejects_the_source_gap_identifier() -> None:
    item = _gap_fill_item()

    assert (
        manual_answer_key_from_model_content(
            item=item,
            content={"1": _GAP_IDS[1], "2": "pear"},
        )
        is None
    )


def test_gap_proposal_preserves_a_valid_human_answer() -> None:
    item = _gap_fill_item()

    key = manual_answer_key_from_model_content(
        item=item,
        content={"1": "apple", "2": "pear"},
    )

    assert isinstance(key, DigiExamOverlayGapFillManualAnswerKey)
    assert tuple(answer.accepted_values for answer in key.gap_answers) == (
        ("apple",),
        ("pear",),
    )
