"""Adversarial tests for AI answer-key suggestions kept on each question.

TASK-SKRIPT-39-04-07 terms T2, T5 and T6: the fingerprint changes for every
answer-relevant edit and for no other edit; an arriving suggestion never
overwrites a teacher, source or reviewed key; restoring and reviewing set
the stated origins; a fingerprint mismatch reports the suggestion as out
of date; save and reopen keep the suggestion.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_fingerprint,
    apply_suggestion_to_item,
    restore_suggestion_on_item,
    suggestion_is_outdated,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAnswerKeySuggestion,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)

pytestmark = pytest.mark.unit

_FINGERPRINT = "a" * 64


def _review(
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_COMPLETE,
) -> NativeItemReview:
    return NativeItemReview(state=state, parse_origin=NativeParseOrigin.TEACHER_CREATED)


def _choice_item(**overrides: object) -> NativeExamItem:
    fields: dict[str, object] = {
        "item_id": "item_001",
        "sequence": 1,
        "kind": NativeExamItemKind.SINGLE_CHOICE,
        "title": "Flervalsfråga",
        "body": (NativeParagraph(segments=(NativeTextSegment(text="Vilket är huvudordet?"),)),),
        "points": 1,
        "choices": (
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
        ),
        "answer_key": NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        "review": _review(),
    }
    fields.update(overrides)
    return NativeExamItem.model_validate(fields)


def _suggestion(
    choice_id: str = "choice_002", fingerprint: str = _FINGERPRINT
) -> NativeAnswerKeySuggestion:
    return NativeAnswerKeySuggestion(
        correct_choice_ids=(choice_id,),
        fingerprint=fingerprint,
        provider_profile_id="profile",
        model="model",
        prompt_template_version="v1",
    )


def _parent(instruction: tuple[str, ...]) -> NativeExamParent:
    return NativeExamParent(
        parent_id="parent_001",
        instruction=instruction,
        item_ids=("item_001",),
    )


class TestFingerprint:
    def test_changes_for_every_answer_relevant_edit(self) -> None:
        item = _choice_item()
        base = answer_key_fingerprint(item, None)

        stem_changed = _choice_item(
            body=(NativeParagraph(segments=(NativeTextSegment(text="Vilket är subjektet?"),)),)
        )
        choice_text_changed = _choice_item(
            choices=(
                NativeChoice(choice_id="choice_001", text="vägen"),
                NativeChoice(choice_id="choice_002", text="lärarna"),
            )
        )
        choice_added = _choice_item(
            choices=(
                NativeChoice(choice_id="choice_001", text="vägen"),
                NativeChoice(choice_id="choice_002", text="eleverna"),
                NativeChoice(choice_id="choice_003", text="skolan"),
            )
        )
        kind_changed = _choice_item(kind=NativeExamItemKind.MULTIPLE_RESPONSE)

        for changed in (stem_changed, choice_text_changed, choice_added, kind_changed):
            assert answer_key_fingerprint(changed, None) != base

    def test_changes_for_parent_instruction_edit(self) -> None:
        item = _choice_item()

        assert answer_key_fingerprint(item, _parent(("Välj rätt ord.",))) != answer_key_fingerprint(
            item, _parent(("Välj fel ord.",))
        )
        assert answer_key_fingerprint(item, None) != answer_key_fingerprint(
            item, _parent(("Välj rätt ord.",))
        )

    def test_changes_for_gap_and_match_edits(self) -> None:
        gap_item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Hon heter "),
                        NativeGapSegment(gap_id="gap_001"),
                        NativeTextSegment(text="."),
                    )
                ),
            ),
            points=1,
            gaps=(NativeGap(gap_id="gap_001"),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
            review=_review(),
        )
        gap_moved = gap_item.model_copy(
            update={
                "body": (
                    NativeParagraph(
                        segments=(
                            NativeGapSegment(gap_id="gap_001"),
                            NativeTextSegment(text=" heter hon."),
                        )
                    ),
                )
            }
        )
        assert answer_key_fingerprint(gap_item, None) != answer_key_fingerprint(gap_moved, None)

        match_item = NativeExamItem(
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
        match_changed = match_item.model_copy(
            update={
                "match_right": (
                    NativeMatchRight(right_id="right_001", text="dog"),
                    NativeMatchRight(right_id="right_002", text="bird"),
                )
            }
        )
        assert answer_key_fingerprint(match_item, None) != answer_key_fingerprint(
            match_changed, None
        )

    def test_unchanged_for_non_answer_relevant_edits(self) -> None:
        item = _choice_item()
        base = answer_key_fingerprint(item, None)

        variants = [
            _choice_item(title="En annan titel"),
            _choice_item(title=None),
            _choice_item(points=5),
            _choice_item(printed_label="Fråga 9"),
            _choice_item(review=_review(NativeItemReviewState.REVIEW_REQUIRED)),
            _choice_item(
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                    correct_choice_ids=("choice_001",),
                )
            ),
            item.model_copy(update={"sequence": 7}),
        ]
        for variant in variants:
            assert answer_key_fingerprint(variant, None) == base


class TestApplySuggestion:
    @pytest.mark.parametrize(
        "origin",
        [
            NativeAnswerKeyOrigin.TEACHER_AUTHORED,
            NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            NativeAnswerKeyOrigin.REVIEWED_ADVISORY,
        ],
    )
    def test_never_overwrites_a_trusted_key(self, origin: NativeAnswerKeyOrigin) -> None:
        item = _choice_item(
            answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=("choice_001",))
        )

        arrived = apply_suggestion_to_item(item, _suggestion("choice_002"))

        assert arrived.answer_key.origin is origin
        assert arrived.answer_key.correct_choice_ids == ("choice_001",)
        assert arrived.review.state is NativeItemReviewState.REVIEW_COMPLETE
        # ...but the suggestion itself is kept on the question.
        assert arrived.ai_suggestion is not None
        assert arrived.ai_suggestion.correct_choice_ids == ("choice_002",)

    def test_new_suggestion_replaces_key_that_is_the_previous_suggestion(self) -> None:
        first = apply_suggestion_to_item(_choice_item(), _suggestion("choice_002"))
        assert first.answer_key.correct_choice_ids == ("choice_002",)

        second = apply_suggestion_to_item(first, _suggestion("choice_001"))

        assert second.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED
        assert second.answer_key.correct_choice_ids == ("choice_001",)
        assert second.ai_suggestion is not None
        assert second.ai_suggestion.correct_choice_ids == ("choice_001",)

    def test_teacher_key_after_a_suggestion_is_kept_on_next_arrival(self) -> None:
        suggested = apply_suggestion_to_item(_choice_item(), _suggestion("choice_002"))
        teacher_keyed = suggested.model_copy(
            update={
                "answer_key": NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                    correct_choice_ids=("choice_001",),
                )
            }
        )

        arrived = apply_suggestion_to_item(teacher_keyed, _suggestion("choice_002"))

        assert arrived.answer_key.origin is NativeAnswerKeyOrigin.TEACHER_AUTHORED
        assert arrived.answer_key.correct_choice_ids == ("choice_001",)


class TestRestoreAndOutdated:
    def test_restore_makes_the_suggestion_the_key_again(self) -> None:
        suggested = apply_suggestion_to_item(_choice_item(), _suggestion("choice_002"))
        teacher_keyed = suggested.model_copy(
            update={
                "answer_key": NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                    correct_choice_ids=("choice_001",),
                ),
                "review": _review(),
            }
        )

        restored = restore_suggestion_on_item(teacher_keyed)

        assert restored.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED
        assert restored.answer_key.correct_choice_ids == ("choice_002",)
        assert restored.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert restored.ai_suggestion is not None

    def test_restore_without_a_suggestion_changes_nothing(self) -> None:
        item = _choice_item()
        assert restore_suggestion_on_item(item) is item

    def test_outdated_after_an_answer_relevant_edit_only(self) -> None:
        item = _choice_item()
        suggestion = _suggestion(fingerprint=answer_key_fingerprint(item, None))
        kept = item.model_copy(update={"ai_suggestion": suggestion})
        assert suggestion_is_outdated(kept, None) is False

        retitled = kept.model_copy(update={"title": "Ny titel"})
        assert suggestion_is_outdated(retitled, None) is False

        reworded = _choice_item(
            choices=(
                NativeChoice(choice_id="choice_001", text="vägen"),
                NativeChoice(choice_id="choice_002", text="lärarna"),
            )
        ).model_copy(update={"ai_suggestion": suggestion})
        assert suggestion_is_outdated(reworded, None) is True


class TestSuggestionStorage:
    def test_historical_suggestion_with_a_removed_choice_is_kept(self) -> None:
        item = _choice_item(
            choices=(
                NativeChoice(choice_id="choice_001", text="vägen"),
                NativeChoice(choice_id="choice_003", text="skolan"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                correct_choice_ids=("choice_001",),
            ),
            ai_suggestion=_suggestion("choice_002"),
        )

        assert item.ai_suggestion is not None
        assert item.ai_suggestion.correct_choice_ids == ("choice_002",)
        assert item.answer_key.correct_choice_ids == ("choice_001",)
        assert suggestion_is_outdated(item, None) is True

    def test_historical_matching_suggestion_with_a_removed_entry_is_kept(self) -> None:
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
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_001"),),
            ),
            ai_suggestion=NativeAnswerKeySuggestion(
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_009"),),
                fingerprint=_FINGERPRINT,
                provider_profile_id="profile",
                model="model",
                prompt_template_version="v1",
            ),
            review=_review(),
        )

        assert item.ai_suggestion is not None
        assert item.ai_suggestion.match_pairs[0].right_id == "right_009"

    def test_historical_gap_suggestion_for_a_removed_gap_is_kept(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Hon heter "),
                        NativeGapSegment(gap_id="gap_001"),
                        NativeTextSegment(text="."),
                    )
                ),
            ),
            points=1,
            gaps=(NativeGap(gap_id="gap_001", accepted_values=("Anna",)),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
            ai_suggestion=NativeAnswerKeySuggestion(
                gap_accepted_values=(
                    NativeGapAcceptedValues(gap_id="gap_002", accepted_values=("Bo",)),
                ),
                fingerprint=_FINGERPRINT,
                provider_profile_id="profile",
                model="model",
                prompt_template_version="v1",
            ),
            review=_review(),
        )

        assert item.ai_suggestion is not None
        assert item.ai_suggestion.gap_accepted_values[0].gap_id == "gap_002"
        assert item.gaps[0].accepted_values == ("Anna",)

    def test_active_key_with_undeclared_choice_is_still_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _choice_item(
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                    correct_choice_ids=("choice_009",),
                )
            )

    def test_save_and_reopen_keep_the_suggestion(self) -> None:
        item = apply_suggestion_to_item(_choice_item(), _suggestion("choice_002"))
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Omprov",
            items=(item,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        reopened = parse_native_exam_document(native_exam_document_json_bytes(document))

        kept = reopened.items[0].ai_suggestion
        assert kept is not None
        assert kept.correct_choice_ids == ("choice_002",)
        assert kept.provider_profile_id == "profile"
        assert kept.model == "model"
        assert kept.prompt_template_version == "v1"
        assert reopened.items[0].answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED


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

    def test_restoring_a_kind_incompatible_suggestion_is_still_refused(self) -> None:
        item = NativeExamItem.model_validate(
            {
                **self._item_fields(NativeExamItemKind.SINGLE_CHOICE),
                "ai_suggestion": self._shapes()["multiple_response"],
            }
        )

        with pytest.raises(ValidationError):
            restore_suggestion_on_item(item)

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

        arrived = apply_suggestion_to_item(item, suggestion)

        assert arrived.answer_key.match_pairs == suggestion.match_pairs
        assert arrived.ai_suggestion == suggestion
