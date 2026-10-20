"""Contract-first change-type matrix, including nested questions and empty scaffolds."""

import random
from decimal import Decimal

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_change_type_test_support import (
    CHOICE_KINDS,
    GAP_KINDS,
    KINDS,
    expected_dropped,
    gap_fill_with_kept_word,
    inline_choice_with_kept_word,
    source_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import matching_item
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import parent_over


def _text_segments(item: NativeExamItem) -> tuple:
    return tuple(
        (paragraph.heading_level, segment)
        for paragraph in item.body
        for segment in paragraph.segments
        if not isinstance(segment, NativeGapSegment)
    )


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
    before_text = _text_segments(item)
    after_text = _text_segments(actual)
    if target is NativeExamItemKind.GAP_FILL and source not in GAP_KINDS:
        # D9: the new gap sits at the end of the last question paragraph, so one
        # unmarked " " separator may follow the otherwise preserved wording.
        assert after_text[: len(before_text)] == before_text
        added = after_text[len(before_text) :]
        assert len(added) <= 1
        if added:
            (heading, separator) = added[0]
            assert heading == item.body[-1].heading_level
            assert (
                isinstance(separator, NativeTextSegment)
                and separator.text == " "
                and separator.marks == ()
            )
        last = actual.body[-1]
        assert isinstance(last.segments[-1], NativeGapSegment)
        assert len(last.segments) > 1
    else:
        assert after_text == before_text
    assert changed.items[1] == sibling
    assert changed.parents == document.parents
    assert changed.document_id == document.document_id
    assert changed.revision == document.revision
    assert changed.origin == document.origin
    assert document.model_dump(mode="json") == before, "Input must remain immutable"
    assert set(result.dropped_content) == expected_dropped(item, target)
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


def test_retype_to_free_text_sets_the_house_default_writing_lines() -> None:
    document = make_document(make_gap_fill_item())
    result = change_item_type(
        document, item_id="item_001", target_kind=NativeExamItemKind.FREE_TEXT, rng=random.Random(1)
    )
    assert result.document.items[0].writing_lines == DEFAULT_WRITING_LINES


def test_retype_from_free_text_drops_the_writing_lines() -> None:
    document = make_document(make_free_text_item())
    result = change_item_type(
        document,
        item_id="item_001",
        target_kind=NativeExamItemKind.SINGLE_CHOICE,
        rng=random.Random(1),
    )
    assert result.document.items[0].writing_lines is None


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


def test_v5_document_is_rejected_without_an_old_reader() -> None:
    payload = make_document(make_free_text_item()).model_dump()
    payload["schema_version"] = "native_exam_document_v5"

    with pytest.raises(ValidationError, match="native_exam_document_v10"):
        NativeExamDocument.model_validate(payload)


@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
def test_a_type_change_keeps_source_points(target: NativeExamItemKind) -> None:
    item = make_free_text_item().model_copy(update={"source_points": 4})

    result = change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )

    assert result.document.items[0].source_points == 4


def _visible_words(item: NativeExamItem) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (segment.text, segment.marks)
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    )


def _kept_links(item: NativeExamItem) -> tuple[str | None, ...]:
    return tuple(
        segment.kept_gap_id
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    )


@pytest.mark.parametrize(
    "target",
    [
        NativeExamItemKind.FREE_TEXT,
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
        NativeExamItemKind.MATCHING,
        NativeExamItemKind.ORDERING,
    ],
    ids=lambda kind: kind.value,
)
def test_retype_gap_fill_with_kept_word_to_plain_kind_drops_kept_answers(
    target: NativeExamItemKind,
) -> None:
    item = gap_fill_with_kept_word()

    result = change_item_type(
        make_document(item), item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )

    changed = result.document.items[0]
    assert changed.kind is target
    assert changed.kept_gaps == ()
    assert all(link is None for link in _kept_links(changed))
    assert _visible_words(changed) == (("Ange frastyp: ", ()), (" NF", ("bold",)))
    assert changed.points == item.points == 2
    assert "accepted_values" in result.dropped_content
    NativeExamDocument.model_validate(result.document.model_dump())


def test_retype_gap_fill_with_kept_word_to_inline_choice_transforms_kept_gap() -> None:
    item = gap_fill_with_kept_word()

    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.INLINE_CHOICE,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.INLINE_CHOICE
    assert len(changed.kept_gaps) == 1
    kept = changed.kept_gaps[0]
    assert kept.gap_id == "gap_002"
    assert [
        segment.text
        for option in kept.options
        for paragraph in option.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ] == ["NF", "nominalfras"]
    assert [option.choice_id for option in kept.options] == ["choice_001", "choice_002"]
    assert kept.correct_option_id == "choice_001"
    assert kept.accepted_values == ()
    assert kept.automatic_values == ()
    assert kept.excluded_automatic_values == ()
    assert "gap_002" in _kept_links(changed)
    assert _visible_words(changed) == (("Ange frastyp: ", ()), (" NF", ("bold",)))
    assert "accepted_values" not in result.dropped_content
    NativeExamDocument.model_validate(result.document.model_dump())


def test_retype_inline_choice_with_kept_word_to_gap_fill_drops_kept_options() -> None:
    item = inline_choice_with_kept_word()
    word = _visible_words(item)[1][0]

    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.GAP_FILL
    assert changed.kept_gaps == ()
    assert all(link is None for link in _kept_links(changed))
    assert _visible_words(changed)[1] == (word, ())
    assert changed.points == item.points
    assert "options" in result.dropped_content
    assert "correct_option_id" in result.dropped_content
    NativeExamDocument.model_validate(result.document.model_dump())


def test_retype_inline_choice_with_kept_word_to_free_text_drops_kept_options() -> None:
    item = inline_choice_with_kept_word()
    word = _visible_words(item)[1][0]

    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.FREE_TEXT,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.FREE_TEXT
    assert changed.kept_gaps == ()
    assert all(link is None for link in _kept_links(changed))
    assert _visible_words(changed)[1] == (word, ())
    assert set(result.dropped_content) == {"gaps", "options", "correct_option_id"}
