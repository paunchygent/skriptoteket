"""Ordering retype, export blockers and server-side refusals (TASK-SKRIPT-39-06-08 D3, D4, P21)."""

import json
import random

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_workspace import RetryExamWorkspaceItemRequest
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    item_has_trusted_key,
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent_commands import (
    add_child,
    create_parent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    make_ordering_item,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import matching_item
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import parent_over

ORDERING = NativeExamItemKind.ORDERING


def _texts(item) -> list[str]:
    return [
        segment.text
        for choice in item.choices
        for paragraph in choice.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _retype(item, target, seed: int = 7):
    return change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(seed)
    )


@pytest.mark.parametrize("seed", range(20))
def test_single_choice_becomes_ordering_with_its_choices_as_steps(seed: int) -> None:
    item = make_single_choice_item()
    assert item.answer_key.correct_choice_ids
    result = _retype(item, ORDERING, seed)
    changed = result.document.items[0]
    assert changed.kind is ORDERING
    assert _texts(changed) == _texts(item)
    assert [c.choice_id for c in changed.choices] == [c.choice_id for c in item.choices]
    assert changed.answer_key.origin is NativeAnswerKeyOrigin.TEACHER_AUTHORED
    assert changed.answer_key.correct_choice_ids == ()
    assert sorted(changed.print_order) == sorted(c.choice_id for c in changed.choices)
    assert changed.print_order != tuple(c.choice_id for c in changed.choices)
    assert changed.points == item.points
    assert result.dropped_content == ("correct_choice_ids",)
    assert "print_order" not in result.dropped_content


def test_free_text_without_points_becomes_ordering_with_blank_steps_and_one_point() -> None:
    item = make_free_text_item().model_copy(update={"points": None})
    changed = _retype(item, ORDERING).document.items[0]
    assert len(changed.choices) == 2
    assert all(not text.strip() for text in _texts(changed))
    assert changed.points == 1
    assert changed.points_estimated is False
    assert changed.print_order != tuple(c.choice_id for c in changed.choices)


def test_free_text_with_points_keeps_them() -> None:
    item = make_free_text_item().model_copy(update={"points": 3})
    assert _retype(item, ORDERING).document.items[0].points == 3


def test_gap_fill_becomes_ordering_without_gap_segments() -> None:
    item = make_gap_fill_item(accepted=("NF",), automatic=())
    result = _retype(item, ORDERING)
    changed = result.document.items[0]
    assert changed.gaps == ()
    assert not any(isinstance(s, NativeGapSegment) for p in changed.body for s in p.segments)
    assert "gaps" in result.dropped_content


@pytest.mark.parametrize(
    "target", [NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE]
)
def test_ordering_becomes_choice_keeping_steps_with_absent_key(
    target: NativeExamItemKind,
) -> None:
    item = make_ordering_item()
    result = _retype(item, target)
    changed = result.document.items[0]
    assert changed.choices == item.choices
    assert changed.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    assert changed.answer_key.correct_choice_ids == ()
    assert changed.print_order == ()
    assert result.dropped_content == ()


def test_one_step_ordering_gets_a_second_choice_for_multiple_response() -> None:
    item = make_ordering_item(steps=("Ensam",), print_order=("choice_001",))
    changed = _retype(item, NativeExamItemKind.MULTIPLE_RESPONSE).document.items[0]
    assert [c.choice_id for c in changed.choices] == ["choice_001", "choice_002"]
    assert _texts(changed) == ["Ensam"]
    assert changed.choices[1].body == ()
    assert changed.print_order == ()


def test_ordering_to_free_text_drops_steps_and_clears_print_order() -> None:
    result = _retype(make_ordering_item(), NativeExamItemKind.FREE_TEXT)
    changed = result.document.items[0]
    assert changed.choices == () and changed.print_order == ()
    assert result.dropped_content == ("choices",)


def test_ordering_to_matching_still_builds_the_grid() -> None:
    changed = _retype(make_ordering_item(), NativeExamItemKind.MATCHING).document.items[0]
    assert len(changed.match_left) == 1 and len(changed.match_right) == 2
    assert changed.print_order == () and changed.choices == ()
    assert changed.tick_points is not None


def test_free_text_to_matching_is_unchanged() -> None:
    item = make_free_text_item().model_copy(update={"points": 2})
    changed = _retype(item, NativeExamItemKind.MATCHING).document.items[0]
    assert len(changed.match_right) == 2
    assert len(changed.answer_key.match_pairs) == 1


def test_matching_to_ordering_gives_blank_steps_and_reports_the_grid() -> None:
    result = _retype(matching_item(), ORDERING)
    changed = result.document.items[0]
    assert changed.match_left == () and changed.answer_key.match_pairs == ()
    assert len(changed.choices) == 2
    assert {"match_left", "match_right", "match_pairs", "tick_points"} <= set(
        result.dropped_content
    )


def test_a_part_child_retyped_to_ordering_is_worth_one_point() -> None:
    document = make_document(
        make_free_text_item(), make_free_text_item(sequence=2, item_id="item_002")
    )
    document = NativeExamDocument.model_validate(
        {**document.model_dump(), "parents": (parent_over("parent_001", "Ctx", 1, 2),)}
    )

    result = change_item_type(
        document, item_id="item_001", target_kind=ORDERING, rng=random.Random(1)
    )

    changed = result.document.items[0]
    assert changed.kind is ORDERING
    assert changed.points == 1
    assert changed.points_estimated is False
    assert result.document.parent_of("item_001") is not None


def _reasons(item) -> list[str]:
    return [b.reason for b in native_export_blockers(make_document(item))]


def test_valid_ordering_has_no_blockers_and_a_trusted_key() -> None:
    item = make_ordering_item()
    assert _reasons(item) == []
    assert item_has_trusted_key(item)


def test_one_step_ordering_blocks_with_too_few_steps() -> None:
    item = make_ordering_item(steps=("Ensam",), print_order=("choice_001",))
    assert _reasons(item) == ["ordering_too_few_steps"]


def test_blank_step_is_an_ordering_blocker_not_a_choice_blocker() -> None:
    item = make_ordering_item(steps=("Först", " "))
    reasons = _reasons(item)
    assert reasons == ["empty_ordering_step"]


def test_blank_choice_stays_an_empty_choice_blocker() -> None:
    payload = make_single_choice_item().model_dump()
    payload["choices"][0]["body"] = plain_body(" ")
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem

    reasons = _reasons(NativeExamItem.model_validate(payload))
    assert "empty_choice" in reasons and "empty_ordering_step" not in reasons


def _parented_exam() -> NativeExamDocument:
    document = make_document(
        make_free_text_item(), make_free_text_item(sequence=2, item_id="item_002")
    )
    return NativeExamDocument.model_validate(
        {**document.model_dump(), "parents": (parent_over("parent_001", "Ctx", 1, 2),)}
    )


def test_add_child_sets_an_ordering_child_to_one_point() -> None:
    result = add_child(
        _parented_exam(),
        parent_id="parent_001",
        child=make_ordering_item(points=3),
        position=0,
    )

    part = result.parents[0]
    added = result.item_by_id(part.item_ids[0])
    assert added.kind is ORDERING
    assert added.points == 1
    assert added.points_estimated is False


def test_create_parent_sets_an_ordering_child_to_one_point() -> None:
    document = make_document(make_free_text_item())

    result = create_parent(
        document, instruction=(), child=make_ordering_item(item_id="item_009", points=3), position=0
    )

    part = result.parents[0]
    created = result.item_by_id(part.item_ids[0])
    assert created.kind is ORDERING
    assert created.points == 1
    assert created.points_estimated is False


def test_import_schema_never_offers_ordering() -> None:
    kinds = [kind for kind in NativeExamItemKind if kind is not ORDERING]
    spec = docx_build_output_spec(anchors=["a"], kinds=kinds)
    assert "ordering" not in json.dumps(spec.json_schema)


@pytest.mark.parametrize("field", ["kind", "conflict_kind"])
def test_contract_rejects_ordering_kinds(field: str) -> None:
    fields = ProducedItem.model_fields
    assert field in fields
    with pytest.raises(ValidationError, match="never produces ordering"):
        ProducedItem.model_validate({field: "ordering"})


def test_retry_request_rejects_ordering() -> None:
    document = make_document(make_free_text_item())
    with pytest.raises(ValidationError, match="never produces ordering"):
        RetryExamWorkspaceItemRequest(document=document, item_id="item_001", kind=ORDERING)
