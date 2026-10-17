"""Dropdown fixtures with gap-local option IDs and deliberately reversed placement."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_gap_fill_item,
    plain_body,
)


def inline_choice_payload(*, sequence: int = 1, points: float | None = 2.01) -> dict:
    payload = make_gap_fill_item(sequence=sequence, item_id=f"item_{sequence:03d}").model_dump(
        mode="json"
    )
    payload.update(
        kind="inline_choice",
        points=points,
        body=[
            {
                "heading_level": None,
                "segments": [
                    {"kind": "text", "text": "Beta & <två>: ", "marks": []},
                    {"kind": "gap", "gap_id": "gap_002"},
                    {"kind": "text", "text": "; alfa: ", "marks": []},
                    {"kind": "gap", "gap_id": "gap_001"},
                ],
            }
        ],
        gaps=[
            {
                "gap_id": f"gap_{number:03d}",
                "options": [
                    {
                        "choice_id": f"choice_{option:03d}",
                        "body": [
                            paragraph.model_dump(mode="json")
                            for paragraph in plain_body(f"{label} {option} & <text>")
                        ],
                    }
                    for option in (1, 2, 3)
                ],
                "correct_option_id": f"choice_{number:03d}",
            }
            for number, label in ((1, "Alfa"), (2, "Beta"))
        ],
    )
    return payload


def inline_choice_item(*, sequence: int = 1, points: float | None = 2.01) -> NativeExamItem:
    return NativeExamItem.model_validate(inline_choice_payload(sequence=sequence, points=points))
