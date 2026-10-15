"""Adversarial tests for suggestions kept across a change of question kind.

TASK-SKRIPT-39-04-07 terms T2 and T6 (F4): a kept suggestion is historical
data for the question its fingerprint describes. It stays stored on a
question of every current kind, is validated only by its own shape, and is
reported out of date once the kind or any other answer-relevant content
changed, including a change to free_text, which has no keyed view.
"""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_fingerprint,
    suggestion_is_outdated,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeAnswerKeySuggestion,
    NativeChoice,
    NativeGap,
    NativeGapAcceptedValues,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_FINGERPRINT = "a" * 64


def _review(
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_COMPLETE,
) -> NativeItemReview:
    return NativeItemReview(state=state, parse_origin=NativeParseOrigin.TEACHER_CREATED)


class TestSuggestionStorageAcrossKindChanges:
    """A kept suggestion is validated only by its own shape (F4 matrix).

    Every produced suggestion shape must stay stored on a question of every
    current kind, with a valid current key for that kind; malformed shapes
    must be rejected on every current kind.
    """

    @staticmethod
    def _item_fields(kind: NativeExamItemKind) -> dict[str, object]:
        base: dict[str, object] = {
            "item_id": "item_001",
            "sequence": 1,
            "kind": kind,
            "body": (NativeParagraph(segments=(NativeTextSegment(text="Fråga?"),)),),
            "points": 1,
            "review": _review(),
        }
        if kind in (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE):
            base["choices"] = (
                NativeChoice(choice_id="choice_001", text="ett"),
                NativeChoice(choice_id="choice_002", text="två"),
                NativeChoice(choice_id="choice_003", text="tre"),
            )
            base["answer_key"] = NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                correct_choice_ids=("choice_001",),
            )
        elif kind is NativeExamItemKind.GAP_FILL:
            base["body"] = (
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Hon heter "),
                        NativeGapSegment(gap_id="gap_001"),
                        NativeTextSegment(text="."),
                    )
                ),
            )
            base["gaps"] = (NativeGap(gap_id="gap_001", accepted_values=("Anna",)),)
            base["answer_key"] = NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED)
        elif kind is NativeExamItemKind.MATCHING:
            base["match_left"] = (NativeMatchLeft(left_id="left_001", text="hund"),)
            base["match_right"] = (
                NativeMatchRight(right_id="right_001", text="dog"),
                NativeMatchRight(right_id="right_002", text="cat"),
            )
            base["answer_key"] = NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_001"),),
            )
        else:
            base["answer_key"] = NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE)
        return base

    @staticmethod
    def _shapes() -> dict[str, NativeAnswerKeySuggestion]:
        lineage = {
            "fingerprint": _FINGERPRINT,
            "provider_profile_id": "profile",
            "model": "model",
            "prompt_template_version": "v1",
        }
        return {
            "single_choice": NativeAnswerKeySuggestion(
                correct_choice_ids=("choice_002",), **lineage
            ),
            "multiple_response": NativeAnswerKeySuggestion(
                correct_choice_ids=("choice_001", "choice_002"), **lineage
            ),
            "gap_fill": NativeAnswerKeySuggestion(
                gap_accepted_values=(
                    NativeGapAcceptedValues(gap_id="gap_001", accepted_values=("Bo",)),
                ),
                **lineage,
            ),
            "matching": NativeAnswerKeySuggestion(
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_002"),),
                **lineage,
            ),
        }

    @pytest.mark.parametrize("kind", list(NativeExamItemKind))
    @pytest.mark.parametrize(
        "shape", ["single_choice", "multiple_response", "gap_fill", "matching"]
    )
    def test_every_suggestion_shape_is_kept_on_every_current_kind(
        self, kind: NativeExamItemKind, shape: str
    ) -> None:
        suggestion = self._shapes()[shape]

        item = NativeExamItem.model_validate(
            {**self._item_fields(kind), "ai_suggestion": suggestion}
        )

        assert item.ai_suggestion == suggestion

    @staticmethod
    def _malformed() -> dict[str, dict[str, object]]:
        pair = NativeMatchPair(left_id="left_001", right_id="right_001")
        gap = NativeGapAcceptedValues(gap_id="gap_001", accepted_values=("Bo",))
        return {
            "empty": {},
            "choice_and_gap": {
                "correct_choice_ids": ("choice_001",),
                "gap_accepted_values": (gap,),
            },
            "choice_and_match": {"correct_choice_ids": ("choice_001",), "match_pairs": (pair,)},
            "match_and_gap": {"match_pairs": (pair,), "gap_accepted_values": (gap,)},
            "duplicate_choices": {"correct_choice_ids": ("choice_001", "choice_001")},
            "duplicate_match_left": {
                "match_pairs": (pair, NativeMatchPair(left_id="left_001", right_id="right_002"))
            },
            "duplicate_match_right": {
                "match_pairs": (pair, NativeMatchPair(left_id="left_002", right_id="right_001"))
            },
            "duplicate_gap": {"gap_accepted_values": (gap, gap)},
        }

    @pytest.mark.parametrize("kind", list(NativeExamItemKind))
    @pytest.mark.parametrize(
        "malformed",
        [
            "empty",
            "choice_and_gap",
            "choice_and_match",
            "match_and_gap",
            "duplicate_choices",
            "duplicate_match_left",
            "duplicate_match_right",
            "duplicate_gap",
        ],
    )
    def test_malformed_suggestion_shapes_are_rejected_on_every_current_kind(
        self, kind: NativeExamItemKind, malformed: str
    ) -> None:
        payload = {
            **self._malformed()[malformed],
            "fingerprint": _FINGERPRINT,
            "provider_profile_id": "profile",
            "model": "model",
            "prompt_template_version": "v1",
        }

        with pytest.raises(ValidationError):
            NativeExamItem.model_validate({**self._item_fields(kind), "ai_suggestion": payload})

    def test_matching_suggestion_pairs_every_left_entry(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.MATCHING,
            body=(NativeParagraph(segments=(NativeTextSegment(text="Para ihop."),)),),
            points=1,
            match_left=(NativeMatchLeft(left_id="left_001", text="hund"),),
            match_right=(
                NativeMatchRight(right_id="right_001", text="dog"),
                NativeMatchRight(right_id="right_002", text="cat"),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
            review=_review(),
        )
        suggestion = NativeAnswerKeySuggestion(
            match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_002"),),
            fingerprint=_FINGERPRINT,
            provider_profile_id="profile",
            model="model",
            prompt_template_version="v1",
        )

        keyed = NativeExamItem.model_validate(
            {
                **dict(item),
                "ai_suggestion": suggestion,
                "answer_key": NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED,
                    match_pairs=suggestion.match_pairs,
                ),
            }
        )

        assert keyed.answer_key.match_pairs == suggestion.match_pairs
        assert keyed.ai_suggestion == suggestion


_SHAPE_KINDS: dict[str, NativeExamItemKind] = {
    "single_choice": NativeExamItemKind.SINGLE_CHOICE,
    "multiple_response": NativeExamItemKind.MULTIPLE_RESPONSE,
    "gap_fill": NativeExamItemKind.GAP_FILL,
    "matching": NativeExamItemKind.MATCHING,
}


class TestOutdatedAcrossKindChanges:
    """Every kept shape reports its currency on every current kind (F4 remainder).

    Each suggestion carries the fingerprint of the keyed question it was
    made for. On that unchanged question it is current; on a question of
    any other kind, free_text included, it is out of date, and the report
    never raises.
    """

    @staticmethod
    def _made_for(shape: str) -> NativeAnswerKeySuggestion:
        original = NativeExamItem.model_validate(
            TestSuggestionStorageAcrossKindChanges._item_fields(_SHAPE_KINDS[shape])
        )
        stored = TestSuggestionStorageAcrossKindChanges._shapes()[shape]
        return stored.model_copy(update={"fingerprint": answer_key_fingerprint(original, None)})

    @pytest.mark.parametrize("kind", list(NativeExamItemKind))
    @pytest.mark.parametrize("shape", list(_SHAPE_KINDS))
    def test_outdated_exactly_when_the_kind_changed(
        self, kind: NativeExamItemKind, shape: str
    ) -> None:
        suggestion = self._made_for(shape)
        item = NativeExamItem.model_validate(
            {
                **TestSuggestionStorageAcrossKindChanges._item_fields(kind),
                "ai_suggestion": suggestion,
            }
        )

        assert suggestion_is_outdated(item, None) is (kind is not _SHAPE_KINDS[shape])

    @pytest.mark.parametrize("kind", list(NativeExamItemKind))
    def test_without_a_suggestion_nothing_is_outdated(self, kind: NativeExamItemKind) -> None:
        item = NativeExamItem.model_validate(
            TestSuggestionStorageAcrossKindChanges._item_fields(kind)
        )

        assert suggestion_is_outdated(item, None) is False
