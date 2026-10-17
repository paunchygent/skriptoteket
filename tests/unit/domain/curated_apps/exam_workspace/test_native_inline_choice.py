"""Adversarial save-boundary contracts for dropdown Lucktext (39-06-04)."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
    inline_choice_payload,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body


@pytest.mark.parametrize("parented", [False, True])
def test_json_save_reopen_keeps_gap_local_options_and_keys(parented: bool) -> None:
    item = inline_choice_item()
    document = document_of((item,))
    if parented:
        document = NativeExamDocument.model_validate(
            {
                **document.model_dump(),
                "parents": (
                    NativeExamParent(
                        parent_id="parent_001",
                        instruction=plain_body("Välj i varje lucka."),
                        item_ids=(item.item_id,),
                    ),
                ),
            }
        )
    reopened = NativeExamDocument.model_validate_json(document.model_dump_json())
    assert reopened == document
    assert reopened.items[0].kind.value == "inline_choice"
    assert [gap.correct_option_id for gap in reopened.items[0].gaps] == ["choice_001", "choice_002"]
    assert [body_plain_text(gap.options[0].body) for gap in reopened.items[0].gaps] == [
        "Alfa 1 & <text>",
        "Beta 1 & <text>",
    ]


@pytest.mark.parametrize(
    "defect",
    [
        "missing_options",
        "empty_options",
        "missing_key",
        "null_key",
        "foreign_key",
        "multiple_keys",
        "duplicate_option_ids",
        "typed_values",
        "automatic_values",
        "excluded_values",
        "no_gaps",
        "top_level_choices",
        "absent_origin",
        "duplicate_gap_ids",
        "missing_placement",
        "duplicate_placement",
        "unknown_placement",
        "nested_gap_option",
    ],
)
def test_malformed_dropdown_cannot_be_saved(defect: str) -> None:
    payload = inline_choice_payload()
    gap = payload["gaps"][0]
    segments = payload["body"][0]["segments"]
    if defect == "missing_options":
        del gap["options"]
    elif defect == "empty_options":
        gap["options"] = []
    elif defect == "missing_key":
        del gap["correct_option_id"]
    elif defect == "null_key":
        gap["correct_option_id"] = None
    elif defect == "foreign_key":
        gap["correct_option_id"] = "choice_099"
    elif defect == "multiple_keys":
        gap["correct_option_id"] = ["choice_001", "choice_002"]
    elif defect == "duplicate_option_ids":
        gap["options"][1]["choice_id"] = "choice_001"
    elif defect == "typed_values":
        gap["accepted_values"] = ["Alfa"]
    elif defect == "automatic_values":
        gap["automatic_values"] = ["Alfa"]
    elif defect == "excluded_values":
        gap["excluded_automatic_values"] = ["Alfa"]
    elif defect == "no_gaps":
        payload["gaps"] = []
    elif defect == "top_level_choices":
        payload["choices"] = gap["options"]
    elif defect == "absent_origin":
        payload["answer_key"]["origin"] = "absent"
    elif defect == "duplicate_gap_ids":
        payload["gaps"][1]["gap_id"] = "gap_001"
    elif defect == "missing_placement":
        segments.pop()
    elif defect == "duplicate_placement":
        segments.append({"kind": "gap", "gap_id": "gap_001"})
    elif defect == "unknown_placement":
        segments[-1]["gap_id"] = "gap_099"
    elif defect == "nested_gap_option":
        gap["options"][0]["body"][0]["segments"] = [{"kind": "gap", "gap_id": "gap_001"}]
    else:
        raise AssertionError(defect)
    with pytest.raises(ValidationError):
        NativeExamItem.model_validate(payload)


def test_switching_dropdown_to_typed_gap_does_not_silently_drop_its_options() -> None:
    payload = inline_choice_payload()
    payload["kind"] = "gap_fill"
    for gap in payload["gaps"]:
        gap["accepted_values"] = ["typed answer"]
    with pytest.raises(ValidationError):
        NativeExamItem.model_validate(payload)
