"""Table-driven tests for the rule that decides whether an arriving suggestion becomes the key.

TASK-SKRIPT-39-04-07 T5 as amended by P12: an arriving suggestion is always
kept on its question; it becomes the key, as ``machine_proposed`` with review
required, only where the question has no key or its key is an unreviewed
``machine_proposed`` key equal to the previous suggestion. A source, teacher or
reviewed key stays even when it equals the previous suggestion. Restoring the
kept suggestion (T6) makes it the key from any origin.

The rows follow the P12 matrix in the retained design note
``evidence/implementation/TASK-SKRIPT-39-04-07/p12/design.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_suggestion_rules import (
    MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON,
    apply_suggestion_to_item,
    restore_suggestion_on_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAnswerKeySuggestion,
    NativeChoice,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)

pytestmark = pytest.mark.unit

_ORIGIN = NativeAnswerKeyOrigin
_STATE = NativeItemReviewState
_TRUSTED = (_ORIGIN.SOURCE_PROVIDED, _ORIGIN.TEACHER_AUTHORED, _ORIGIN.REVIEWED_ADVISORY)
_BOTH_STATES = (_STATE.REVIEW_REQUIRED, _STATE.REVIEW_COMPLETE)

_KEY = ("choice_001",)
_OTHER = ("choice_003",)
_ARRIVING_DIFFERS = ("choice_002",)


@dataclass(frozen=True)
class _Relation:
    """How the key compares with the previous and the arriving suggestion."""

    name: str
    previous: tuple[str, ...] | None
    arriving: tuple[str, ...]


_NO_PREVIOUS = _Relation("no_previous", None, _ARRIVING_DIFFERS)
_NO_PREVIOUS_ARRIVING_EQUALS_KEY = _Relation("no_previous_arriving_equals_key", None, _KEY)
_EQUALS_PREVIOUS = _Relation("key_equals_previous", _KEY, _ARRIVING_DIFFERS)
_EQUALS_PREVIOUS_AND_ARRIVING = _Relation("key_equals_previous_and_arriving", _KEY, _KEY)
_DIFFERS = _Relation("key_differs_from_both", _OTHER, _ARRIVING_DIFFERS)
_DIFFERS_EQUALS_ARRIVING = _Relation("key_differs_from_previous_equals_arriving", _OTHER, _KEY)
_ALL_RELATIONS = (
    _NO_PREVIOUS,
    _NO_PREVIOUS_ARRIVING_EQUALS_KEY,
    _EQUALS_PREVIOUS,
    _EQUALS_PREVIOUS_AND_ARRIVING,
    _DIFFERS,
    _DIFFERS_EQUALS_ARRIVING,
)


def _rows(
    matrix_row: str,
    origins: tuple[NativeAnswerKeyOrigin, ...],
    states: tuple[NativeItemReviewState, ...],
    relations: tuple[_Relation, ...],
    *,
    becomes_key: bool,
) -> list[object]:
    return [
        pytest.param(
            origin,
            state,
            relation,
            becomes_key,
            id=f"row{matrix_row}-{origin.value}-{state.value}-{relation.name}",
        )
        for origin in origins
        for state in states
        for relation in relations
    ]


_MATRIX = [
    *_rows(
        "3-4",
        (_ORIGIN.MACHINE_PROPOSED,),
        (_STATE.REVIEW_REQUIRED,),
        (_EQUALS_PREVIOUS, _EQUALS_PREVIOUS_AND_ARRIVING),
        becomes_key=True,
    ),
    *_rows(
        "5-7",
        (_ORIGIN.MACHINE_PROPOSED,),
        (_STATE.REVIEW_REQUIRED,),
        (_DIFFERS, _DIFFERS_EQUALS_ARRIVING, _NO_PREVIOUS, _NO_PREVIOUS_ARRIVING_EQUALS_KEY),
        becomes_key=False,
    ),
    *_rows(
        "8-10",
        (_ORIGIN.MACHINE_PROPOSED,),
        (_STATE.REVIEW_COMPLETE,),
        _ALL_RELATIONS,
        becomes_key=False,
    ),
    *_rows("11-15", _TRUSTED, _BOTH_STATES, _ALL_RELATIONS, becomes_key=False),
]


def _choice_item(
    *,
    kind: NativeExamItemKind = NativeExamItemKind.SINGLE_CHOICE,
    answer_key: NativeAnswerKey,
    state: NativeItemReviewState,
    previous: NativeAnswerKeySuggestion | None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=kind,
        title="Flervalsfråga",
        body=(NativeParagraph(segments=(NativeTextSegment(text="Vilket är huvudordet?"),)),),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
            NativeChoice(choice_id="choice_003", text="skolan"),
        ),
        answer_key=answer_key,
        review=NativeItemReview(state=state, parse_origin=NativeParseOrigin.TEACHER_CREATED),
        ai_suggestion=previous,
    )


def _suggestion(choice_ids: tuple[str, ...]) -> NativeAnswerKeySuggestion:
    return NativeAnswerKeySuggestion(
        correct_choice_ids=choice_ids,
        fingerprint="a" * 64,
        provider_profile_id="profile",
        model="model",
        prompt_template_version="v1",
    )


def _assert_became_key(arrived: NativeExamItem, arriving: NativeAnswerKeySuggestion) -> None:
    assert arrived.ai_suggestion == arriving
    assert arrived.answer_key.origin is _ORIGIN.MACHINE_PROPOSED
    assert arrived.answer_key.correct_choice_ids == arriving.correct_choice_ids
    assert arrived.review.state is _STATE.REVIEW_REQUIRED
    assert arrived.review.reasons.count(MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON) == 1


def _assert_key_stayed(
    arrived: NativeExamItem, item: NativeExamItem, arriving: NativeAnswerKeySuggestion
) -> None:
    assert arrived.ai_suggestion == arriving
    assert arrived.answer_key == item.answer_key
    assert arrived.review == item.review


class TestArrivalRule:
    @pytest.mark.parametrize(("origin", "state", "relation", "becomes_key"), _MATRIX)
    def test_keyed_question(
        self,
        origin: NativeAnswerKeyOrigin,
        state: NativeItemReviewState,
        relation: _Relation,
        becomes_key: bool,
    ) -> None:
        previous = None if relation.previous is None else _suggestion(relation.previous)
        item = _choice_item(
            answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=_KEY),
            state=state,
            previous=previous,
        )
        arriving = _suggestion(relation.arriving)

        arrived = apply_suggestion_to_item(item, arriving)

        if becomes_key:
            _assert_became_key(arrived, arriving)
        else:
            _assert_key_stayed(arrived, item, arriving)

    @pytest.mark.parametrize("state", _BOTH_STATES)
    @pytest.mark.parametrize("previous", [None, _ARRIVING_DIFFERS, _OTHER])
    def test_keyless_question_takes_the_suggestion_as_key(
        self, state: NativeItemReviewState, previous: tuple[str, ...] | None
    ) -> None:
        item = _choice_item(
            answer_key=NativeAnswerKey(origin=_ORIGIN.ABSENT),
            state=state,
            previous=None if previous is None else _suggestion(previous),
        )
        arriving = _suggestion(_ARRIVING_DIFFERS)

        _assert_became_key(apply_suggestion_to_item(item, arriving), arriving)

    def test_key_equal_to_the_previous_suggestion_in_another_order_follows_it(self) -> None:
        item = _choice_item(
            kind=NativeExamItemKind.MULTIPLE_RESPONSE,
            answer_key=NativeAnswerKey(
                origin=_ORIGIN.MACHINE_PROPOSED,
                correct_choice_ids=("choice_001", "choice_002"),
            ),
            state=_STATE.REVIEW_REQUIRED,
            previous=_suggestion(("choice_002", "choice_001")),
        )
        arriving = _suggestion(("choice_003",))

        _assert_became_key(apply_suggestion_to_item(item, arriving), arriving)

    def test_free_text_question_keeps_its_not_applicable_key(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            title="Fritext",
            body=(NativeParagraph(segments=(NativeTextSegment(text="Förklara."),)),),
            points=2,
            answer_key=NativeAnswerKey(origin=_ORIGIN.NOT_APPLICABLE),
            review=NativeItemReview(
                state=_STATE.REVIEW_REQUIRED, parse_origin=NativeParseOrigin.TEACHER_CREATED
            ),
        )
        arriving = _suggestion(_ARRIVING_DIFFERS)

        _assert_key_stayed(apply_suggestion_to_item(item, arriving), item, arriving)


class TestRestoreIgnoresTheArrivalRule:
    @pytest.mark.parametrize(
        "origin",
        [_ORIGIN.MACHINE_PROPOSED, *_TRUSTED],
    )
    @pytest.mark.parametrize("state", _BOTH_STATES)
    def test_restore_makes_a_kept_suggestion_the_key_from_any_origin(
        self, origin: NativeAnswerKeyOrigin, state: NativeItemReviewState
    ) -> None:
        item = _choice_item(
            answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=_KEY),
            state=state,
            previous=None,
        )
        stayed = apply_suggestion_to_item(item, _suggestion(_ARRIVING_DIFFERS))
        assert stayed.answer_key.origin is origin

        restored = restore_suggestion_on_item(stayed)

        _assert_became_key(restored, _suggestion(_ARRIVING_DIFFERS))
