"""Adversarial tests for the two conditions an arriving suggestion must meet to become the key.

TASK-SKRIPT-39-04-07 T5 as amended by P12 and P13:

- Whole-key equality (P12). An unreviewed ``machine_proposed`` key follows
  an arrival only when it equals the previous suggestion as a whole key. The
  choice ids, the match pairs and the gap-id-to-values map must each be
  equal as sets. An extra historical gap id or any other missing or extra
  entry makes them unequal.
- Fit (P13). An arrival that would not be a valid key for the question's
  current kind and ids is stored on the question and never becomes the key,
  whatever the key's origin.

Rows follow case spaces B and D in the retained design note
``evidence/implementation/TASK-SKRIPT-39-04-07/repair3/design.md``.
"""

from dataclasses import dataclass

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_suggestion_rules import (
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
    NativeGap,
    NativeGapAcceptedValues,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError

pytestmark = pytest.mark.unit

_FINGERPRINT = "a" * 64

GapValues = tuple[tuple[str, tuple[str, ...]], ...]
Pairs = tuple[tuple[str, str], ...]


def _review(state: NativeItemReviewState) -> NativeItemReview:
    return NativeItemReview(state=state, parse_origin=NativeParseOrigin.TEACHER_CREATED)


def _suggestion(
    choices: tuple[str, ...] = (), pairs: Pairs = (), gaps: GapValues = ()
) -> NativeAnswerKeySuggestion:
    return NativeAnswerKeySuggestion(
        correct_choice_ids=choices,
        match_pairs=tuple(NativeMatchPair(left_id=left, right_id=right) for left, right in pairs),
        gap_accepted_values=tuple(
            NativeGapAcceptedValues(gap_id=gap_id, accepted_values=values)
            for gap_id, values in gaps
        ),
        fingerprint=_FINGERPRINT,
        provider_profile_id="profile",
        model="model",
        prompt_template_version="v1",
    )


def _key(
    origin: NativeAnswerKeyOrigin, choices: tuple[str, ...] = (), pairs: Pairs = ()
) -> NativeAnswerKey:
    return NativeAnswerKey(
        origin=origin,
        correct_choice_ids=choices,
        match_pairs=tuple(NativeMatchPair(left_id=left, right_id=right) for left, right in pairs),
    )


def _choice_item(
    kind: NativeExamItemKind,
    key: NativeAnswerKey,
    previous: NativeAnswerKeySuggestion | None,
    choice_ids: tuple[str, ...] = ("choice_001", "choice_002", "choice_003"),
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_REQUIRED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=kind,
        body=(NativeParagraph(segments=(NativeTextSegment(text="Vilka är verb?"),)),),
        points=1,
        choices=tuple(
            NativeChoice(choice_id=choice_id, text=choice_id) for choice_id in choice_ids
        ),
        answer_key=key,
        ai_suggestion=previous,
        review=_review(state),
    )


def _matching_item(
    key: NativeAnswerKey,
    previous: NativeAnswerKeySuggestion | None,
    left_ids: tuple[str, ...] = ("left_001", "left_002", "left_003"),
    right_ids: tuple[str, ...] = ("right_001", "right_002", "right_003"),
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_REQUIRED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.MATCHING,
        body=(NativeParagraph(segments=(NativeTextSegment(text="Para ihop."),)),),
        points=1,
        match_left=tuple(NativeMatchLeft(left_id=left_id, text=left_id) for left_id in left_ids),
        match_right=tuple(
            NativeMatchRight(right_id=right_id, text=right_id) for right_id in right_ids
        ),
        answer_key=key,
        ai_suggestion=previous,
        review=_review(state),
    )


def _gap_item(
    origin: NativeAnswerKeyOrigin,
    key: GapValues,
    previous: NativeAnswerKeySuggestion | None,
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_REQUIRED,
) -> NativeExamItem:
    segments: list[NativeTextSegment | NativeGapSegment] = [NativeTextSegment(text="Hon heter ")]
    for gap_id, _values in key:
        segments += [NativeGapSegment(gap_id=gap_id), NativeTextSegment(text=" och ")]
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(NativeParagraph(segments=tuple(segments)),),
        points=1,
        gaps=tuple(NativeGap(gap_id=gap_id, accepted_values=values) for gap_id, values in key),
        answer_key=NativeAnswerKey(origin=origin),
        ai_suggestion=previous,
        review=_review(state),
    )


_MP = NativeAnswerKeyOrigin.MACHINE_PROPOSED
_ABSENT = NativeAnswerKeyOrigin.ABSENT
_KEY_PAIRS: Pairs = (
    ("left_001", "right_002"),
    ("left_002", "right_001"),
    ("left_003", "right_003"),
)
_ARRIVING_CHOICES = _suggestion(choices=("choice_003",))
_ARRIVING_PAIR_IDS: Pairs = (
    ("left_001", "right_003"),
    ("left_002", "right_002"),
    ("left_003", "right_001"),
)
_ARRIVING_PAIRS = _suggestion(pairs=_ARRIVING_PAIR_IDS)
_ARRIVING_GAPS = _suggestion(gaps=(("gap_001", ("Bo",)), ("gap_002", ("Umeå",))))


@dataclass(frozen=True)
class _Row:
    name: str
    item: NativeExamItem
    arriving: NativeAnswerKeySuggestion
    becomes_key: bool


def _multi(key: tuple[str, ...], previous: tuple[str, ...]) -> NativeExamItem:
    return _choice_item(
        NativeExamItemKind.MULTIPLE_RESPONSE, _key(_MP, choices=key), _suggestion(choices=previous)
    )


def _match(key: Pairs, previous: Pairs) -> NativeExamItem:
    return _matching_item(_key(_MP, pairs=key), _suggestion(pairs=previous))


def _gaps(key: GapValues, previous: GapValues) -> NativeExamItem:
    return _gap_item(_MP, key, _suggestion(gaps=previous))


_EQUALITY_ROWS = [
    _Row(
        "B4 reordered choices",
        _multi(("choice_001", "choice_002"), ("choice_002", "choice_001")),
        _ARRIVING_CHOICES,
        True,
    ),
    _Row(
        "B5 previous is a subset",
        _multi(("choice_001", "choice_002"), ("choice_001",)),
        _ARRIVING_CHOICES,
        False,
    ),
    _Row(
        "B3 previous is a superset",
        _multi(("choice_001",), ("choice_001", "choice_002")),
        _ARRIVING_CHOICES,
        False,
    ),
    _Row(
        "B6 duplicated key choice",
        _multi(("choice_001", "choice_001"), ("choice_001", "choice_002")),
        _ARRIVING_CHOICES,
        False,
    ),
    _Row(
        "B7 previous also names a removed choice",
        _multi(("choice_001", "choice_002"), ("choice_001", "choice_002", "choice_009")),
        _ARRIVING_CHOICES,
        False,
    ),
    _Row(
        "B8 reordered pairs", _match(_KEY_PAIRS, tuple(reversed(_KEY_PAIRS))), _ARRIVING_PAIRS, True
    ),
    _Row(
        "B9 previous pairs are a subset", _match(_KEY_PAIRS, _KEY_PAIRS[:2]), _ARRIVING_PAIRS, False
    ),
    _Row(
        "B10 previous holds an extra historical pair",
        _match(_KEY_PAIRS, (*_KEY_PAIRS, ("left_009", "right_009"))),
        _ARRIVING_PAIRS,
        False,
    ),
    _Row(
        "B12 reordered values per gap",
        _gaps(
            (("gap_001", ("Anna", "Anne")), ("gap_002", ("Lund",))),
            (("gap_001", ("Anne", "Anna")), ("gap_002", ("Lund",))),
        ),
        _ARRIVING_GAPS,
        True,
    ),
    _Row(
        "B13 one gap's values are a subset",
        _gaps(
            (("gap_001", ("Anna", "Anne")), ("gap_002", ("Lund",))),
            (("gap_001", ("Anna",)), ("gap_002", ("Lund",))),
        ),
        _ARRIVING_GAPS,
        False,
    ),
    _Row(
        "B14 previous holds an extra historical gap id",
        _gaps(
            (("gap_001", ("Anna",)), ("gap_002", ("Lund",))),
            (("gap_001", ("Anna",)), ("gap_002", ("Lund",)), ("gap_009", ("Malmö",))),
        ),
        _ARRIVING_GAPS,
        False,
    ),
    _Row(
        "B15 previous lacks a gap the key fills",
        _gaps((("gap_001", ("Anna",)), ("gap_002", ("Lund",))), (("gap_001", ("Anna",)),)),
        _ARRIVING_GAPS,
        False,
    ),
    _Row(
        "B17 duplicated key value",
        _gaps(
            (("gap_001", ("Anna", "Anna")), ("gap_002", ("Lund",))),
            (("gap_001", ("Anna", "Anne")), ("gap_002", ("Lund",))),
        ),
        _ARRIVING_GAPS,
        False,
    ),
    _Row(
        "B18 a duplicated key value accepts nothing more",
        _gaps(
            (("gap_001", ("Anna", "Anna")), ("gap_002", ("Lund",))),
            (("gap_001", ("Anna",)), ("gap_002", ("Lund",))),
        ),
        _ARRIVING_GAPS,
        True,
    ),
    _Row(
        "B19 a choice key never equals a gap suggestion",
        _choice_item(
            NativeExamItemKind.MULTIPLE_RESPONSE,
            _key(_MP, choices=("choice_001",)),
            _suggestion(gaps=(("gap_001", ("choice_001",)),)),
        ),
        _ARRIVING_CHOICES,
        False,
    ),
]

_GAP_KEY: GapValues = (("gap_001", ("Anna",)), ("gap_002", ("Lund",)))

_FIT_ROWS = [
    _Row(
        "D1 single choice names a removed choice",
        _choice_item(
            NativeExamItemKind.SINGLE_CHOICE, _key(_ABSENT), None, ("choice_001", "choice_002")
        ),
        _ARRIVING_CHOICES,
        False,
    ),
    _Row(
        "D2 multi names one removed choice",
        _choice_item(
            NativeExamItemKind.MULTIPLE_RESPONSE, _key(_ABSENT), None, ("choice_001", "choice_002")
        ),
        _suggestion(choices=("choice_001", "choice_003")),
        False,
    ),
    _Row(
        "D3 multi with declared choices in another order",
        _choice_item(NativeExamItemKind.MULTIPLE_RESPONSE, _key(_ABSENT), None),
        _suggestion(choices=("choice_003", "choice_001")),
        True,
    ),
    _Row(
        "D4 matching pairs a removed left entry",
        _matching_item(_key(_ABSENT), None, left_ids=("left_001", "left_002")),
        _ARRIVING_PAIRS,
        False,
    ),
    _Row(
        "D5 matching misses a left entry the teacher added",
        _matching_item(
            _key(_ABSENT), None, left_ids=("left_001", "left_002", "left_003", "left_004")
        ),
        _ARRIVING_PAIRS,
        False,
    ),
    _Row(
        "D6 matching names a removed right entry",
        _matching_item(_key(_ABSENT), None, right_ids=("right_001", "right_002")),
        _ARRIVING_PAIRS,
        False,
    ),
    _Row(
        "D7 matching with declared pairs in another order",
        _matching_item(_key(_ABSENT), None),
        _suggestion(pairs=tuple(reversed(_ARRIVING_PAIR_IDS))),
        True,
    ),
    _Row(
        "D8 gap names a removed gap",
        _gap_item(_ABSENT, (("gap_001", ()),), None),
        _ARRIVING_GAPS,
        False,
    ),
    _Row(
        "D9 gap misses a gap the teacher added",
        _gap_item(_ABSENT, (("gap_001", ()), ("gap_002", ()), ("gap_003", ())), None),
        _ARRIVING_GAPS,
        False,
    ),
    _Row(
        "D10 gap with the same gaps in another order",
        _gap_item(_ABSENT, (("gap_002", ()), ("gap_001", ())), None),
        _ARRIVING_GAPS,
        True,
    ),
    _Row(
        "D8 on a key that follows its previous suggestion",
        _gap_item(_MP, (("gap_001", ("Anna",)),), _suggestion(gaps=(("gap_001", ("Anna",)),))),
        _ARRIVING_GAPS,
        False,
    ),
]


def _assert_outcome(row: _Row) -> None:
    arrived = apply_suggestion_to_item(row.item, row.arriving)

    assert arrived.ai_suggestion == row.arriving
    if row.becomes_key:
        assert arrived.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED
        assert set(arrived.answer_key.correct_choice_ids) == set(row.arriving.correct_choice_ids)
        assert set(arrived.answer_key.match_pairs) == set(row.arriving.match_pairs)
        assert {
            gap.gap_id: set(gap.accepted_values) for gap in arrived.gaps if gap.accepted_values
        } == {
            entry.gap_id: set(entry.accepted_values) for entry in row.arriving.gap_accepted_values
        }
        assert arrived.review.state is NativeItemReviewState.REVIEW_REQUIRED
    else:
        assert arrived.answer_key == row.item.answer_key
        assert arrived.gaps == row.item.gaps
        assert arrived.review == row.item.review


class TestWholeKeyEquality:
    @pytest.mark.parametrize("row", _EQUALITY_ROWS, ids=lambda row: row.name)
    def test_machine_key_follows_only_an_equal_whole_previous_suggestion(self, row: _Row) -> None:
        _assert_outcome(row)


class TestFit:
    @pytest.mark.parametrize("row", _FIT_ROWS, ids=lambda row: row.name)
    def test_arrival_that_does_not_fit_is_stored_and_never_the_key(self, row: _Row) -> None:
        _assert_outcome(row)

    def test_restore_refuses_a_suggestion_that_does_not_fit(self) -> None:
        item = _choice_item(
            NativeExamItemKind.SINGLE_CHOICE,
            _key(NativeAnswerKeyOrigin.TEACHER_AUTHORED, choices=("choice_001",)),
            _suggestion(choices=("choice_003",)),
            ("choice_001", "choice_002"),
        )

        with pytest.raises(DomainError):
            restore_suggestion_on_item(item)
