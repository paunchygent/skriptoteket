"""Retyping a source_fallback item flips origin but keeps it in review."""

import random

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    is_unbuilt_question,
    is_unreviewed_retyped_question,
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeItemReview
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    make_review,
    make_single_choice_item,
)

_FALLBACK_REASONS = ("Frågan kunde inte konverteras.",)


def _fallback_review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_REQUIRED,
        parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
        confidence=None,
        reasons=_FALLBACK_REASONS,
    )


def _fallback_item(base: NativeExamItem) -> NativeExamItem:
    return base.model_copy(update={"review": _fallback_review()})


def _reasons(item: NativeExamItem) -> set[str]:
    return {blocker.reason for blocker in native_export_blockers(make_document(item))}


def test_retype_source_fallback_free_text_to_gap_fill_keeps_review_and_reasons() -> None:
    item = _fallback_item(make_free_text_item())

    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.GAP_FILL
    assert len(changed.gaps) == 1
    assert changed.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert changed.review.parse_origin is NativeParseOrigin.TEACHER_RETYPED
    assert changed.review.confidence is None
    assert changed.review.reasons == _FALLBACK_REASONS
    assert not is_unbuilt_question(changed)
    assert is_unreviewed_retyped_question(changed)


@pytest.mark.parametrize(
    "base",
    [make_free_text_item(), make_gap_fill_item()],
    ids=["free_text", "gap_fill"],
)
def test_same_kind_on_fallback_flips_only_origin(base: NativeExamItem) -> None:
    item = _fallback_item(base)

    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=item.kind,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is item.kind
    assert changed.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert changed.review.parse_origin is NativeParseOrigin.TEACHER_RETYPED
    assert changed.review.confidence == item.review.confidence
    assert changed.review.reasons == item.review.reasons
    assert result.dropped_content == ()
    assert changed == item.model_copy(
        update={
            "review": item.review.model_copy(
                update={"parse_origin": NativeParseOrigin.TEACHER_RETYPED}
            )
        }
    )


@pytest.mark.parametrize(
    "origin",
    [NativeParseOrigin.LLM_PARSED, NativeParseOrigin.DETERMINISTIC],
    ids=["llm_parsed", "deterministic"],
)
def test_same_kind_without_fallback_stays_a_noop(origin: NativeParseOrigin) -> None:
    item = make_single_choice_item().model_copy(
        update={
            "review": make_review(state=NativeItemReviewState.REVIEW_REQUIRED, parse_origin=origin)
        }
    )
    document = make_document(item)

    result = change_item_type(
        document, item_id=item.item_id, target_kind=item.kind, rng=random.Random(1)
    )

    assert result.document is document
    assert result.dropped_content == ()


def test_different_kind_retype_of_llm_parsed_item_keeps_llm_parsed() -> None:
    item = make_single_choice_item().model_copy(
        update={
            "review": make_review(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.LLM_PARSED,
            )
        }
    )

    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.FREE_TEXT,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.FREE_TEXT
    assert changed.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert changed.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert not is_unreviewed_retyped_question(changed)


def test_retyped_item_blocks_export_with_new_reason_until_reviewed() -> None:
    item = _fallback_item(make_free_text_item())
    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    )
    retyped = result.document.items[0]

    reasons = _reasons(retyped)
    assert "unreviewed_retyped_question" in reasons
    assert "unbuilt_question" not in reasons

    reviewed = retyped.model_copy(
        update={
            "review": retyped.review.model_copy(
                update={"state": NativeItemReviewState.REVIEW_COMPLETE}
            )
        }
    )
    assert "unreviewed_retyped_question" not in _reasons(reviewed)


@pytest.mark.parametrize(
    "origin",
    [NativeParseOrigin.LLM_PARSED, NativeParseOrigin.DETERMINISTIC],
    ids=["llm_parsed", "deterministic"],
)
def test_converted_item_needing_review_does_not_get_new_reason(origin: NativeParseOrigin) -> None:
    item = make_gap_fill_item().model_copy(
        update={
            "review": make_review(state=NativeItemReviewState.REVIEW_REQUIRED, parse_origin=origin)
        }
    )

    assert "unreviewed_retyped_question" not in _reasons(item)


def test_review_complete_teacher_retyped_item_does_not_get_new_reason() -> None:
    item = make_gap_fill_item().model_copy(
        update={
            "review": make_review(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.TEACHER_RETYPED,
            )
        }
    )

    assert "unreviewed_retyped_question" not in _reasons(item)


def test_review_required_teacher_created_item_does_not_get_new_reason() -> None:
    """review_required + teacher_created predates the retype (AI facit suggestion on a
    teacher-made question, or Ångra granskad on one), so it must not take the new blocker."""
    item = make_gap_fill_item().model_copy(
        update={
            "review": make_review(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.TEACHER_CREATED,
            )
        }
    )

    assert "unreviewed_retyped_question" not in _reasons(item)


def test_teacher_created_item_with_machine_proposed_key_skips_new_reason() -> None:
    """An AI Föreslå facit on a teacher-made question: only the key blocker applies."""
    item = make_single_choice_item(origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED).model_copy(
        update={
            "review": make_review(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.TEACHER_CREATED,
            )
        }
    )

    reasons = _reasons(item)
    assert "unreviewed_retyped_question" not in reasons
    assert "machine_proposed_key_unreviewed" in reasons


def test_review_required_teacher_retyped_item_gets_new_reason() -> None:
    item = make_gap_fill_item().model_copy(
        update={
            "review": make_review(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.TEACHER_RETYPED,
            )
        }
    )

    assert "unreviewed_retyped_question" in _reasons(item)
