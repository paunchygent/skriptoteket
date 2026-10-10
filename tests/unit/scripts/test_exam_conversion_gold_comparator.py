"""Substantive comparison and the shared A10 spelling policy."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from scripts.exam_conversion_eval.compare import compare_exam, compare_items, compare_native_exam
from scripts.exam_conversion_eval.gold import GoldExam, GoldItem
from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
    normalize_answer,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)


def _item(**changes: object) -> GoldItem:
    return GoldItem.model_validate(
        {
            "source_label": "Q1",
            "kind": "free_text",
            "points": 2,
            "prompt": "Explain this.",
            **changes,
        }
    )


def _gap(*answers: tuple[str, ...]) -> GoldItem:
    return _item(
        kind="gap_fill",
        prompt=" ".join("[___]" for _ in answers),
        gaps=tuple({"accepted_values": values} for values in answers),
    )


def _exam(*items: GoldItem) -> GoldExam:
    return GoldExam(source_filename="exam.docx", source_sha256="a" * 64, title="Exam", items=items)


def _native(**changes: object) -> NativeExamItem:
    return NativeExamItem.model_validate(
        {
            "item_id": "item_001",
            "sequence": 1,
            "kind": "free_text",
            "points": 2,
            "body": (NativeParagraph(segments=(NativeTextSegment(text="Explain this."),)),),
            "answer_key": NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            "review": NativeItemReview(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.DETERMINISTIC,
            ),
            **changes,
        }
    )


def _document(item: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Exam",
        items=(item,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def test_prompt_whitespace_and_source_label_do_not_change_substance() -> None:
    assert compare_items(_item(), _item(prompt=" Explain\n  this. ", source_label="other")) == ()


@pytest.mark.parametrize("prompt", ["explain this.", "Explain this!", "Explain this"])
def test_prompt_case_and_punctuation_remain_significant(prompt: str) -> None:
    assert [m.field for m in compare_items(_item(), _item(prompt=prompt))] == ["prompt"]


def test_choice_order_and_whitespace_do_not_matter() -> None:
    expected = _item(
        kind="multiple_response", choices=("a text", "b", "c"), correct_choices=("a text", "b")
    )
    actual = _item(
        kind="multiple_response",
        choices=("c", "b", " a  text "),
        correct_choices=("b", " a  text "),
    )
    assert compare_items(expected, actual) == ()


def test_gap_order_of_answers_and_casefold_whitespace() -> None:
    assert compare_items(_gap(("New York", "NY")), _gap(("ny", " new\n YORK "))) == ()


@pytest.mark.parametrize(
    "gold,extra,allowed",
    [
        ("planet", "palnet", True),
        ("planet", "plxny t", False),
        ("planets", "plxnetsz", True),
        ("planets", "plxnytsz", False),
        ("ca", "abc", False),
        ("cabbbbb", "abcbbbb", True),
        ("New York", "Nwe Yrok", True),
        ("New York", "Nwe Yrokx", False),
    ],
)
def test_length_bounds_transpositions_and_whole_string_policy(
    gold: str, extra: str, allowed: bool
) -> None:
    assert is_allowed_answer_spelling_variant(gold, extra) is allowed
    assert (not compare_items(_gap((gold,)), _gap((gold, extra)))) is allowed


def test_true_damerau_distance_supports_overlapping_edits() -> None:
    # CA -> AC -> ABC, with unchanged suffix; optimal-string-alignment gives 3.
    assert is_allowed_answer_spelling_variant("cabbbbb", "abcbbbb")


def test_spelling_normalization_empty_values_and_other_gold_exclusion() -> None:
    assert normalize_answer(" STRAẞE\n  TWO ") == "strasse two"
    assert is_allowed_answer_spelling_variant(" PLANET ", "palnet")
    assert not is_allowed_answer_spelling_variant("planet", " PLANET ")
    assert not is_allowed_answer_spelling_variant("", "a")
    assert not is_allowed_answer_spelling_variant("a", " ")
    assert not is_allowed_answer_spelling_variant(
        "planet", "palnet", other_gold_answers=(" PALNET ",)
    )


def test_missing_answer_cannot_be_replaced_by_allowed_typo() -> None:
    mismatches = compare_items(_gap(("planet",)), _gap(("palnet",)))
    assert [(m.field, m.reason) for m in mismatches] == [
        ("gaps[0].accepted_values", "missing_answers")
    ]


def test_extra_equal_to_another_gap_gold_fails() -> None:
    mismatches = compare_items(
        _gap(("planet",), ("palnet",)), _gap(("planet", " PALNET "), ("palnet",))
    )
    assert [m.reason for m in mismatches] == ["extra_answers"]


def test_missing_and_unallowed_extra_accumulate() -> None:
    mismatches = compare_items(_gap(("planet",)), _gap(("synonym",)))
    assert [m.reason for m in mismatches] == ["missing_answers", "extra_answers"]


def test_all_field_mismatches_accumulate() -> None:
    expected = _item(kind="single_choice", choices=("a", "b"), correct_choices=("a",))
    actual = _gap(("x",))
    actual = GoldItem.model_validate({**actual.model_dump(), "points": 3})
    assert {m.field for m in compare_items(expected, actual)} == {
        "kind",
        "points",
        "prompt",
        "choices",
        "correct_choices",
        "gaps",
    }


def test_wrong_correct_option_and_options_fail_separately() -> None:
    expected = _item(kind="single_choice", choices=("a", "b"), correct_choices=("a",))
    actual = _item(kind="single_choice", choices=("b", "c"), correct_choices=("b",))
    assert [m.field for m in compare_items(expected, actual)] == ["choices", "correct_choices"]


def test_matching_is_directed_and_unordered_with_whitespace_only() -> None:
    expected = _item(
        kind="matching", pairs=({"left": "A", "right": "B"}, {"left": "C", "right": "D"})
    )
    reordered = _item(
        kind="matching", pairs=({"left": " C ", "right": "D"}, {"left": "A", "right": " B "})
    )
    assert not compare_items(expected, reordered)
    reversed_pair = _item(kind="matching", pairs=({"left": "B", "right": "A"},))
    assert [m.field for m in compare_items(expected, reversed_pair)] == ["pairs"]


def test_exam_order_extra_missing_and_confirmation_metadata() -> None:
    gold = _exam(_item())
    report = compare_exam(gold, (_item(),))
    assert report.passed and report.unconfirmed and report.confirmation_note is None
    assert compare_exam(gold, ()).items[0].mismatches[0].reason == "missing_item"
    extra = compare_exam(gold, (_item(), _item(source_label="Q2")))
    assert not extra.passed
    assert extra.items[1].mismatches[0].reason == "extra_item"
    with pytest.raises(FrozenInstanceError):
        setattr(report, "confirmed", True)
    with pytest.raises(FrozenInstanceError):
        setattr(extra.items[1].mismatches[0], "field", "changed")
    second = _item(source_label="Q2", prompt="Another prompt.")
    reordered = compare_exam(_exam(_item(), second), (second, _item()))
    assert all(not item.passed for item in reordered.items)


def test_unresolved_gold_fails_even_when_equal_or_missing() -> None:
    unresolved = _item(teacher_questions=("What points?",))
    assert compare_items(unresolved, unresolved)[0].reason == "gold_unresolved"
    report = compare_exam(_exam(unresolved), ())
    assert [m.reason for m in report.items[0].mismatches] == ["gold_unresolved", "missing_item"]


def test_native_matching_unsupported_and_review_requires_review_state() -> None:
    matching = _item(kind="matching", pairs=({"left": "A", "right": "B"},))
    assert {
        m.field
        for m in compare_native_exam(_exam(matching), _document(_native())).items[0].mismatches
    } == {"kind", "pairs"}
    review_gold = _exam(_item(kind="review"))
    assert not compare_native_exam(review_gold, _document(_native())).passed
    review = NativeItemReview(
        state=NativeItemReviewState.REVIEW_REQUIRED, parse_origin=NativeParseOrigin.LLM_PARSED
    )
    assert compare_native_exam(review_gold, _document(_native(review=review))).passed


def test_native_gap_body_order_overrides_declaration_order() -> None:
    native = _native(
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                segments=(
                    NativeGapSegment(gap_id="gap_002"),
                    NativeTextSegment(text=" "),
                    NativeGapSegment(gap_id="gap_001"),
                )
            ),
        ),
        gaps=(
            NativeGap(gap_id="gap_001", accepted_values=("one",)),
            NativeGap(gap_id="gap_002", accepted_values=("two",)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
    )
    assert compare_native_exam(_exam(_gap(("two",), ("one",))), _document(native)).passed
    assert not compare_native_exam(_exam(_gap(("one",), ("two",))), _document(native)).passed


def test_native_choices_project_identifiers_to_text_and_absent_keys_to_mismatches() -> None:
    native = _native(
        kind=NativeExamItemKind.SINGLE_CHOICE,
        choices=(
            NativeChoice(choice_id="choice_007", text="a"),
            NativeChoice(choice_id="choice_002", text="b"),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED, correct_choice_ids=("choice_007",)
        ),
    )
    gold = _exam(_item(kind="single_choice", choices=("b", "a"), correct_choices=("a",)))
    assert compare_native_exam(gold, _document(native)).passed
    absent = NativeExamItem.model_validate(
        {**native.model_dump(), "answer_key": {"origin": "absent"}}
    )
    assert [m.field for m in compare_native_exam(gold, _document(absent)).items[0].mismatches] == [
        "correct_choices"
    ]
