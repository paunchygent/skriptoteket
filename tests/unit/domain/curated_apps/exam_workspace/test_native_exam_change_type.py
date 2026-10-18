"""Contract-first change-type matrix, including nested questions and empty scaffolds."""

import random
from decimal import Decimal

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import matching_item
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import parent_over

# Ordering has its own matrix in test_native_exam_ordering_rules.py.
KINDS = tuple(kind for kind in NativeExamItemKind if kind is not NativeExamItemKind.ORDERING)
CHOICE_KINDS = {NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE}
GAP_KINDS = {NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE}


def source_item(kind: NativeExamItemKind) -> NativeExamItem:
    """Independent fixtures with real key data, not copies of the conversion algorithm."""
    if kind is NativeExamItemKind.FREE_TEXT:
        return make_free_text_item()
    if kind is NativeExamItemKind.SINGLE_CHOICE:
        return make_single_choice_item()
    if kind is NativeExamItemKind.MULTIPLE_RESPONSE:
        payload = make_single_choice_item().model_dump()
        payload["kind"] = kind
        payload["answer_key"]["correct_choice_ids"] = ("choice_001", "choice_002")
        return NativeExamItem.model_validate(payload)
    if kind is NativeExamItemKind.GAP_FILL:
        return make_gap_fill_item(accepted=("NF", "nominalfras"), automatic=("nf",))
    if kind is NativeExamItemKind.INLINE_CHOICE:
        return inline_choice_item(points=2)
    return matching_item()


def _text_segments(item: NativeExamItem) -> tuple:
    return tuple(
        (paragraph.heading_level, segment)
        for paragraph in item.body
        for segment in paragraph.segments
        if not isinstance(segment, NativeGapSegment)
    )


def _expected_dropped(source: NativeExamItem, target: NativeExamItemKind) -> set[str]:
    """What the target cannot represent, specified independently of production output."""
    if source.kind is target:
        return set()
    dropped: set[str] = set()
    if source.kind in CHOICE_KINDS:
        if target not in CHOICE_KINDS:
            dropped.update(("choices", "correct_choice_ids"))
        elif (
            target is NativeExamItemKind.SINGLE_CHOICE
            and len(source.answer_key.correct_choice_ids) > 1
        ):
            dropped.add("correct_choice_ids")
    if source.kind in GAP_KINDS:
        if target not in GAP_KINDS:
            dropped.add("gaps")
        if source.kind is NativeExamItemKind.GAP_FILL:
            if target is not NativeExamItemKind.INLINE_CHOICE:
                dropped.add("accepted_values")
        else:
            dropped.update(("options", "correct_option_id"))
    if source.kind is NativeExamItemKind.MATCHING:
        dropped.update(("match_left", "match_right", "match_pairs", "tick_points"))
    return dropped


@pytest.mark.parametrize("parented", [False, True], ids=["standalone", "child"])
@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
@pytest.mark.parametrize("source", KINDS, ids=lambda kind: kind.value)
def test_every_kind_pair_keeps_text_points_identity_and_parent(
    source: NativeExamItemKind, target: NativeExamItemKind, parented: bool
) -> None:
    item = source_item(source)
    sibling = make_free_text_item(sequence=2, item_id="item_002")
    document = make_document(item, sibling)
    if parented:
        document = NativeExamDocument.model_validate(
            {**document.model_dump(), "parents": (parent_over("parent_001", "Context", 1, 2),)}
        )
    before = document.model_dump(mode="json")

    result = change_item_type(
        document, item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )

    changed = NativeExamDocument.model_validate(result.document.model_dump())
    actual = changed.items[0]
    assert actual.kind is target
    assert actual.item_id == item.item_id
    assert actual.sequence == item.sequence
    assert actual.points == item.points
    assert _text_segments(actual) == _text_segments(item)
    assert changed.items[1] == sibling
    assert changed.parents == document.parents
    assert changed.document_id == document.document_id
    assert changed.revision == document.revision
    assert changed.origin == document.origin
    assert document.model_dump(mode="json") == before, "Input must remain immutable"
    assert set(result.dropped_content) == _expected_dropped(item, target)
    assert len(result.dropped_content) == len(set(result.dropped_content))
    if source is target:
        assert changed == document
    elif source in CHOICE_KINDS and target in CHOICE_KINDS:
        assert actual.choices == item.choices
        if "correct_choice_ids" not in result.dropped_content:
            assert actual.answer_key.correct_choice_ids == item.answer_key.correct_choice_ids
        else:
            assert actual.answer_key.correct_choice_ids == ()
    elif source in GAP_KINDS and target in GAP_KINDS:
        assert actual.body == item.body
        assert [gap.gap_id for gap in actual.gaps] == [gap.gap_id for gap in item.gaps]
    if target not in GAP_KINDS:
        assert actual.gaps == ()
        assert not any(isinstance(s, NativeGapSegment) for p in actual.body for s in p.segments)
    if target not in CHOICE_KINDS:
        assert actual.choices == ()
        assert actual.answer_key.correct_choice_ids == ()
    if target is not NativeExamItemKind.MATCHING:
        assert actual.match_left == actual.match_right == actual.answer_key.match_pairs == ()
        assert actual.tick_points is None


@pytest.mark.parametrize("points", [0, 2, 2.75])
@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
def test_minimum_parts_block_export_until_filled(
    target: NativeExamItemKind, points: int | float
) -> None:
    item = make_free_text_item().model_copy(update={"points": points})
    result = change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )
    changed = result.document.items[0]
    assert changed.points == points
    assert result.dropped_content == ()
    if target is NativeExamItemKind.FREE_TEXT:
        assert native_export_blockers(result.document) == ()
        return
    blockers = native_export_blockers(result.document)
    assert blockers, "Empty parts cannot be exported"
    expected_empty = (
        ("empty_choice", 2)
        if target in CHOICE_KINDS
        else ("empty_gap_option", 2)
        if target is NativeExamItemKind.INLINE_CHOICE
        else ("empty_match_entry", 3)
        if target is NativeExamItemKind.MATCHING
        else ("missing_answer_key", 1)
    )
    assert sum(b.reason == expected_empty[0] for b in blockers) == expected_empty[1]
    payload = changed.model_dump()
    # A review toggle alone must never make empty structure exportable.
    payload["review"]["state"] = "review_complete"
    still_empty = NativeExamItem.model_validate(payload)
    assert native_export_blockers(make_document(still_empty))
    payload["answer_key"]["origin"] = "teacher_authored"
    if target in CHOICE_KINDS:
        assert len(changed.choices) == 2
        assert all(
            isinstance(segment, NativeTextSegment) and not segment.text.strip()
            for choice in changed.choices
            for paragraph in choice.body
            for segment in paragraph.segments
        )
        for index, choice in enumerate(payload["choices"]):
            choice["body"] = plain_body(f"Svar {index + 1}")
        payload["answer_key"]["correct_choice_ids"] = (changed.choices[0].choice_id,)
    elif target in GAP_KINDS:
        assert len(changed.gaps) == 1
        assert sum(isinstance(s, NativeGapSegment) for p in changed.body for s in p.segments) == 1
        gap = payload["gaps"][0]
        if target is NativeExamItemKind.GAP_FILL:
            assert changed.gaps[0].accepted_values == ()
            gap["accepted_values"] = ("Svar",)
        else:
            assert len(changed.gaps[0].options) == 2
            for index, option in enumerate(gap["options"]):
                option["body"] = plain_body(f"Val {index + 1}")
    else:
        assert len(changed.match_left) == 1
        assert len(changed.match_right) == 2  # current matching grid minimum
        assert len(changed.answer_key.match_pairs) == 1
        assert changed.tick_points == Decimal(str(points))
        for entry in payload["match_left"]:
            entry["body"] = plain_body("Begrepp")
        for index, entry in enumerate(payload["match_right"]):
            entry["body"] = plain_body(f"Förklaring {index + 1}")
    filled = NativeExamItem.model_validate(payload)
    assert native_export_blockers(make_document(filled)) == ()
    # Fill every part except one: a valid key and review toggle cannot hide it.
    if target in CHOICE_KINDS:
        payload["choices"][-1]["body"] = plain_body(" \t ")
    elif target is NativeExamItemKind.INLINE_CHOICE:
        payload["gaps"][0]["options"][-1]["body"] = plain_body(" \t ")
    elif target is NativeExamItemKind.MATCHING:
        payload["match_right"][-1]["body"] = plain_body(" \t ")
    else:
        return
    partial = NativeExamItem.model_validate(payload)
    assert native_export_blockers(make_document(partial)), "Every empty part remains a blocker"


@pytest.mark.parametrize("target", [NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE])
def test_matching_loss_includes_zero_tick_points(target: NativeExamItemKind) -> None:
    item = matching_item(tick_points=Decimal("0"), points=0)
    result = change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )
    assert result.document.items[0].points == 0
    assert set(result.dropped_content) == {
        "match_left",
        "match_right",
        "match_pairs",
        "tick_points",
    }


def test_dropped_names_are_per_content_kind_not_per_gap_or_option() -> None:
    document = make_document(inline_choice_item())
    result = change_item_type(
        document, item_id="item_001", target_kind=NativeExamItemKind.FREE_TEXT, rng=random.Random(1)
    )
    assert set(result.dropped_content) == {"gaps", "options", "correct_option_id"}
    assert len(result.dropped_content) == 3


@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
def test_unstated_points_are_not_invented(target: NativeExamItemKind) -> None:
    item = make_free_text_item().model_copy(update={"points": None})
    result = change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )
    assert result.document.items[0].points is None
    assert "missing_points" in {
        blocker.reason for blocker in native_export_blockers(result.document)
    }
    NativeExamDocument.model_validate(result.document.model_dump())


@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
def test_criteria_and_ai_key_are_reported_but_import_wording_is_preserved(
    target: NativeExamItemKind,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        criteria=[{"text": "Förklaring", "points": 4}],
        facit_text="Original teacher wording",
        source_anchor="body:0001",
        printed_label="Fråga 1",
        ai_suggestion={
            "correct_choice_ids": ["choice_001"],
            "fingerprint": "a" * 64,
            "provider_profile_id": "test-profile",
            "model": "test-model",
            "prompt_template_version": "test-template",
        },
    )
    item = NativeExamItem.model_validate(payload)
    result = change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )
    expected = set() if target is NativeExamItemKind.FREE_TEXT else {"criteria", "ai_suggestion"}
    assert set(result.dropped_content) == expected
    changed = result.document.items[0]
    if target is NativeExamItemKind.FREE_TEXT:
        assert changed == item
    else:
        assert changed.criteria == ()
        assert changed.ai_suggestion is None
    assert changed.facit_text == item.facit_text
    assert changed.source_anchor == item.source_anchor
    assert changed.printed_label == item.printed_label


def test_missing_item_is_not_a_silent_noop() -> None:
    document = make_document(make_free_text_item())
    with pytest.raises(DomainError) as error:
        change_item_type(
            document,
            item_id="item_999",
            target_kind=NativeExamItemKind.SINGLE_CHOICE,
            rng=random.Random(1),
        )
    assert error.value.code is ErrorCode.NOT_FOUND


def _retry_source(label_kind: NativeExamItemKind) -> NativeExamRetrySource:
    return NativeExamRetrySource(
        chunks=(
            NativeExamRetryChunk(
                anchor="body:0001",
                kind="paragraph",
                text="Original question wording",
                marked_text="Original question wording",
                runs=(),
                paragraphs=(),
            ),
        ),
        label_kind=label_kind,
    )


@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
@pytest.mark.parametrize(
    ("source", "suggestion"),
    [(source, suggestion) for source in KINDS for suggestion in KINDS if source is not suggestion],
    ids=lambda kind: kind.value,
)
def test_suggestion_is_consumed_only_by_its_target_kind(
    source: NativeExamItemKind,
    suggestion: NativeExamItemKind,
    target: NativeExamItemKind,
) -> None:
    payload = source_item(source).model_dump()
    payload.update(suggested_kind=suggestion, retry_source=_retry_source(suggestion))
    item = NativeExamItem.model_validate(payload)
    sibling_payload = make_free_text_item(sequence=2, item_id="item_002").model_dump()
    sibling_payload.update(
        suggested_kind=NativeExamItemKind.SINGLE_CHOICE,
        retry_source=_retry_source(NativeExamItemKind.SINGLE_CHOICE),
    )
    sibling = NativeExamItem.model_validate(sibling_payload)
    document = make_document(item, sibling)
    before = document.model_dump(mode="json")

    result = change_item_type(
        document, item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )

    changed = result.document.items[0]
    assert changed.kind is target
    assert changed.suggested_kind is (None if target is suggestion else suggestion)
    assert changed.retry_source == item.retry_source
    assert result.document.items[1] == sibling
    assert document.model_dump(mode="json") == before, "Consuming cannot mutate the input"
    assert set(result.dropped_content) == _expected_dropped(item, target)
    assert NativeExamDocument.model_validate(result.document.model_dump()) == result.document
    if target is source:
        assert result.document is document, "A no-op must preserve the pending suggestion"


def test_consumed_suggestion_stays_absent_after_an_unrelated_manual_type_change() -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        suggested_kind=NativeExamItemKind.SINGLE_CHOICE,
        retry_source=_retry_source(NativeExamItemKind.SINGLE_CHOICE),
    )
    original = NativeExamItem.model_validate(payload)
    accepted = change_item_type(
        make_document(original),
        item_id=original.item_id,
        target_kind=NativeExamItemKind.SINGLE_CHOICE,
        rng=random.Random(1),
    ).document
    assert accepted.items[0].suggested_kind is None

    manually_changed = change_item_type(
        accepted,
        item_id=original.item_id,
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    ).document

    changed = manually_changed.items[0]
    assert changed.kind is NativeExamItemKind.GAP_FILL
    assert changed.retry_source == original.retry_source
    assert changed.suggested_kind is None
    assert NativeExamDocument.model_validate(manually_changed.model_dump()) == manually_changed


@pytest.mark.parametrize("label_kind", KINDS, ids=lambda kind: kind.value)
def test_missing_suggestion_is_valid_even_when_the_source_label_differs(
    label_kind: NativeExamItemKind,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.pop("suggested_kind")
    payload["retry_source"] = _retry_source(label_kind)

    item = NativeExamItem.model_validate(payload)

    assert item.suggested_kind is None
    assert item.retry_source is not None
    assert item.retry_source.label_kind is label_kind


@pytest.mark.parametrize(
    ("label_kind", "suggestion", "message"),
    [
        (
            NativeExamItemKind.FREE_TEXT,
            NativeExamItemKind.FREE_TEXT,
            "suggested kind must differ from the item's kind",
        ),
        (None, NativeExamItemKind.SINGLE_CHOICE, "suggested kind requires retry source"),
        (
            NativeExamItemKind.GAP_FILL,
            NativeExamItemKind.SINGLE_CHOICE,
            "suggested kind must match the retry source's label kind",
        ),
    ],
    ids=["already-current-kind", "missing-source", "disagrees-with-label"],
)
def test_invalid_suggested_kind_is_rejected(
    label_kind: NativeExamItemKind | None,
    suggestion: NativeExamItemKind,
    message: str,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        suggested_kind=suggestion,
        retry_source=_retry_source(label_kind) if label_kind is not None else None,
    )

    with pytest.raises(ValidationError, match=message):
        NativeExamItem.model_validate(payload)


@pytest.mark.parametrize("suggestion", [None, NativeExamItemKind.SINGLE_CHOICE])
def test_v6_document_round_trip_stores_suggested_kind(
    suggestion: NativeExamItemKind | None,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        suggested_kind=suggestion,
        retry_source=_retry_source(NativeExamItemKind.SINGLE_CHOICE),
    )
    document = make_document(NativeExamItem.model_validate(payload))

    encoded = native_exam_document_json_bytes(document)
    restored = parse_native_exam_document(encoded)

    assert restored == document
    assert restored.schema_version == "native_exam_document_v6"
    assert restored.items[0].suggested_kind is suggestion
    assert restored.model_dump(mode="json")["items"][0]["suggested_kind"] == (
        suggestion.value if suggestion is not None else None
    )


def test_v5_document_is_rejected_without_an_old_reader() -> None:
    payload = make_document(make_free_text_item()).model_dump()
    payload["schema_version"] = "native_exam_document_v5"

    with pytest.raises(ValidationError, match="native_exam_document_v6"):
        NativeExamDocument.model_validate(payload)
