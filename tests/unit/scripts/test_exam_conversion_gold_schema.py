"""Validation of source-authored gold documents."""

import json

import pytest
from pydantic import BaseModel, ValidationError

from scripts.exam_conversion_eval.gold import GoldExam, GoldGap, GoldItem, GoldPair


def _item(**changes: object) -> GoldItem:
    return GoldItem.model_validate(
        {"source_label": "1", "kind": "free_text", "prompt": "Explain.", **changes}
    )


def _exam(**changes: object) -> GoldExam:
    return GoldExam.model_validate(
        {
            "source_filename": "exam.docx",
            "source_sha256": "a" * 64,
            "title": "Exam",
            "items": (_item(),),
            **changes,
        }
    )


def test_json_round_trip_defaults_and_frozen_models() -> None:
    gold = _exam()
    assert not gold.confirmed
    assert gold.confirmation_note is None
    assert gold.notes == ()
    assert GoldExam.model_validate_json(json.dumps(gold.model_dump(mode="json"))) == gold
    assert GoldExam.model_json_schema()["additionalProperties"] is False
    with pytest.raises(ValidationError, match="frozen"):
        setattr(gold, "title", "Changed")
    with pytest.raises(ValidationError, match="frozen"):
        setattr(gold.items[0], "prompt", "Changed")


@pytest.mark.parametrize("points", [0, -1, float("inf"), float("nan"), True, "2"])
def test_invalid_points(points: object) -> None:
    with pytest.raises(ValidationError, match="positive finite"):
        _item(points=points)


@pytest.mark.parametrize("points", [None, 1, 1.5])
def test_valid_points(points: object) -> None:
    assert _item(points=points).points == points


@pytest.mark.parametrize(
    "changes",
    [
        {"source_filename": "folder/exam.docx"},
        {"source_filename": "folder\\exam.docx"},
        {"source_filename": "exam.pdf"},
        {"source_filename": ".docx"},
        {"source_sha256": "a" * 63},
        {"source_sha256": "z" * 64},
        {"items": ()},
        {"items": (_item(), _item())},
        {"schema_version": "v2"},
        {"unknown": 1},
        {"title": " "},
    ],
)
def test_exam_rejects_malformed_metadata(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _exam(**changes)


@pytest.mark.parametrize("note", [None, "", "   "])
def test_confirmed_needs_note(note: str | None) -> None:
    with pytest.raises(ValidationError, match="confirmed gold"):
        _exam(confirmed=True, confirmation_note=note)


def test_confirmed_rejects_unresolved_teacher_questions() -> None:
    unresolved = _item(teacher_questions=("Which wording?",))
    assert not _exam(items=(unresolved,)).confirmed
    with pytest.raises(ValidationError, match="teacher_questions"):
        _exam(items=(unresolved,), confirmed=True, confirmation_note="Teacher confirmed")
    assert _exam(confirmed=True, confirmation_note="Teacher confirmed").confirmed


@pytest.mark.parametrize(
    "changes",
    [
        {"prompt": " "},
        {"source_label": " "},
        {"unknown": "x"},
        {"kind": "free_text", "choices": ("a", "b")},
        {"kind": "review", "pairs": ({"left": "a", "right": "b"},)},
        {"kind": "single_choice", "choices": ("a", "b"), "correct_choices": ("c",)},
        {"kind": "single_choice", "choices": ("a", "b"), "correct_choices": ()},
        {"kind": "single_choice", "choices": ("a", "b"), "correct_choices": ("a", "b")},
        {"kind": "single_choice", "choices": ("a", " a "), "correct_choices": ("a",)},
        {"kind": "multiple_response", "choices": ("a", "b"), "correct_choices": ()},
        {"kind": "gap_fill", "prompt": "[___]", "gaps": ()},
        {"kind": "gap_fill", "prompt": "[___]", "gaps": ({"accepted_values": ()},)},
        {"kind": "gap_fill", "gaps": ({"accepted_values": ("a",)},)},
        {"kind": "matching", "pairs": ()},
        {"kind": "matching", "pairs": ({"left": "a", "right": "b"},), "choices": ("a",)},
        {"kind": "free_text", "prompt": "[___]"},
    ],
)
def test_item_kind_fields(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _item(**changes)


def test_unresolved_keys_and_matching_are_expressible() -> None:
    _item(kind="single_choice", choices=("a", "b"), teacher_questions=("Which?",))
    _item(
        kind="gap_fill",
        prompt="[___]",
        gaps=(GoldGap(accepted_values=()),),
        teacher_questions=("What answer?",),
    )
    _item(kind="matching", pairs=(GoldPair(left="a", right="b"),))
    _item(kind="review")


def test_matching_accepts_several_pairs_for_one_left_entry() -> None:
    item = _item(
        kind="matching",
        points=4,
        prompt="Sätt ett kryss i rätt kolumn.\nSubstantiv | Verb | Adjektiv\n1. vila",
        pairs=(
            GoldPair(left="vila", right="Substantiv"),
            GoldPair(left="vila", right="Verb"),
        ),
    )
    assert [pair.left for pair in item.pairs] == ["vila", "vila"]
    assert {pair.right for pair in item.pairs} == {"Substantiv", "Verb"}


@pytest.mark.parametrize(
    "model,payload",
    [
        (GoldGap, {"accepted_values": (" ",)}),
        (GoldGap, {"accepted_values": ("a",), "extra": True}),
        (GoldPair, {"left": " ", "right": "a"}),
        (GoldPair, {"left": "a", "right": " ", "extra": True}),
    ],
)
def test_nested_models_reject_blank_values_and_extra_fields(
    model: type[BaseModel], payload: dict
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)
