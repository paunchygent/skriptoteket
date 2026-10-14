"""Parents on the native exam document: invariants proven on the recorded corpus conversions."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamParent,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
    parent_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    recorded_document,
    recorded_items,
)

_LEGACY_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


def _first_same_kind_run(length: int) -> list[int]:
    """Sequence numbers of the first run of `length` consecutive items sharing one kind."""
    items = recorded_items()
    for start in range(len(items) - length + 1):
        window = items[start : start + length]
        if len({item.kind for item in window}) == 1:
            return [item.sequence for item in window]
    raise AssertionError("recording has no such run")


def _kind_boundary() -> tuple[int, int]:
    """Two consecutive sequence numbers whose items have different kinds."""
    items = recorded_items()
    for first, second in zip(items, items[1:], strict=False):
        if first.kind is not second.kind:
            return first.sequence, second.sequence
    raise AssertionError("recording has a single kind")


def _instruction_lines(*lines: str) -> tuple[NativeParagraph, ...]:
    return tuple(NativeParagraph(segments=(NativeTextSegment(text=line),)) for line in lines)


def _parent(parent_id: str, *numbers: int, instruction: tuple[str, ...] = ("Do these.",)):
    return NativeExamParent(
        parent_id=parent_id,
        instruction=_instruction_lines(*instruction),
        item_ids=tuple(f"item_{number:03d}" for number in numbers),
    )


def test_parent_over_a_run_of_one_kind_validates_and_is_found_from_each_child():
    run = _first_same_kind_run(3)
    document = recorded_document((_parent("parent_001", *run),))

    parent = document.parents[0]
    assert [document.parent_of(f"item_{n:03d}") for n in run] == [parent] * 3
    assert document.parent_of(f"item_{run[-1] + 1:03d}") is None


def test_parent_points_sum_the_children_and_are_none_when_a_child_has_none():
    run = _first_same_kind_run(3)
    items = recorded_items()
    document = recorded_document((_parent("parent_001", *run),), items=items)
    parent = document.parents[0]
    scores = [items[n - 1].points for n in run]
    assert None not in scores
    expected = sum(score for score in scores if score is not None)

    assert parent_points(document, parent) == expected

    unscored = items[run[1] - 1].model_copy(update={"points": None})
    broken = document.model_copy(
        update={"items": (*items[: run[1] - 1], unscored, *items[run[1] :])}
    )
    assert parent_points(broken, parent) is None


def test_children_that_skip_an_item_are_rejected():
    first, _, third = _first_same_kind_run(3)

    with pytest.raises(ValidationError, match="consecutive items in sequence order"):
        recorded_document((_parent("parent_001", first, third),))


def test_children_listed_out_of_sequence_order_are_rejected():
    first, second = _first_same_kind_run(2)

    with pytest.raises(ValidationError, match="consecutive items in sequence order"):
        recorded_document((_parent("parent_001", second, first),))


def test_children_of_different_kinds_share_one_parent_and_survive_a_json_round_trip():
    first, second = _kind_boundary()
    items = recorded_items()
    assert items[first - 1].kind is not items[second - 1].kind

    document = recorded_document((_parent("parent_001", first, second),), items=items)
    again = NativeExamDocument.model_validate_json(native_exam_document_json_bytes(document))

    assert again.parents == document.parents
    assert again.parent_of(f"item_{first:03d}") == again.parent_of(f"item_{second:03d}")


def test_a_child_that_is_not_an_item_is_rejected():
    last = len(recorded_items())

    with pytest.raises(ValidationError, match="references unknown items"):
        recorded_document((_parent("parent_001", last, last + 1),))


def test_an_item_under_two_parents_is_rejected():
    first, second, third = _first_same_kind_run(3)

    with pytest.raises(ValidationError, match="belong to more than one parent"):
        recorded_document(
            (_parent("parent_001", first, second), _parent("parent_002", second, third))
        )


def test_a_repeated_parent_id_is_rejected():
    first, second, third, fourth = _first_same_kind_run(4)

    with pytest.raises(ValidationError, match="parent ids must be unique"):
        recorded_document(
            (_parent("parent_001", first, second), _parent("parent_001", third, fourth))
        )


def test_one_child_listed_twice_is_rejected():
    (first, _) = _first_same_kind_run(2)

    with pytest.raises(ValidationError, match="consecutive items in sequence order"):
        recorded_document((_parent("parent_001", first, first),))


@pytest.mark.parametrize(
    "fields",
    [
        {"parent_id": "parent_1"},
        {"parent_id": "item_001"},
        {"instruction": ()},
        {"instruction": (NativeParagraph(segments=(NativeGapSegment(gap_id="gap_001"),)),)},
        {"item_ids": ()},
        {"unknown_field": "x"},
    ],
    ids=[
        "short_id",
        "wrong_prefix",
        "no_instruction",
        "gap_instruction",
        "no_children",
        "extra_field",
    ],
)
def test_malformed_parent_fields_are_rejected(fields: dict):
    valid = {
        "parent_id": "parent_001",
        "instruction": (NativeParagraph(segments=(NativeTextSegment(text="Do these."),)),),
        "item_ids": ("item_001",),
    }

    with pytest.raises(ValidationError):
        NativeExamParent.model_validate({**valid, **fields})


def test_document_saved_without_parents_still_parses_and_keeps_its_schema_version():
    saved = json.loads(native_exam_document_json_bytes(recorded_document()))
    del saved["parents"]

    document = NativeExamDocument.model_validate(saved)

    assert document.parents == ()
    assert document.schema_version == "native_exam_document_v2"


def test_legacy_fixture_without_parents_parses():
    document = NativeExamDocument.model_validate_json(_LEGACY_FIXTURE.read_bytes())

    assert document.parents == ()


def test_parents_survive_a_json_round_trip():
    run = _first_same_kind_run(3)
    document = recorded_document((_parent("parent_001", *run, instruction=("One.", "Two.")),))

    again = NativeExamDocument.model_validate_json(native_exam_document_json_bytes(document))

    assert again.parents == document.parents
    assert body_text_lines(again.parents[0].instruction) == ("One.", "Two.")
