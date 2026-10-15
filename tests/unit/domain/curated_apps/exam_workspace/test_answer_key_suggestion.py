"""Adversarial tests for AI answer-key suggestions kept on each question.

TASK-SKRIPT-39-04-07 terms T2, T5 and T6: the fingerprint changes for every
answer-relevant edit and for no other edit; an arriving suggestion never
overwrites a teacher, source or reviewed key; restoring and reviewing set
the stated origins; a fingerprint mismatch reports the suggestion as out
of date; save and reopen keep the suggestion.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_fingerprint,
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
        instruction=tuple(
            NativeParagraph(segments=(NativeTextSegment(text=text),)) for text in instruction
        ),
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
            tick_points=Decimal("1"),
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


class TestOutdated:
    def test_outdated_after_an_answer_relevant_edit_only(self) -> None:
        item = _choice_item()
        suggestion = _suggestion(fingerprint=answer_key_fingerprint(item, None))
        kept = item.model_copy(update={"ai_suggestion": suggestion})
        assert suggestion_is_outdated(kept, None) is False

        repointed = kept.model_copy(update={"points": 5})
        assert suggestion_is_outdated(repointed, None) is False

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
            tick_points=Decimal("1"),
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
        item = _choice_item(
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED,
                correct_choice_ids=("choice_002",),
            ),
            review=_review(NativeItemReviewState.REVIEW_REQUIRED),
            ai_suggestion=_suggestion("choice_002"),
        )
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
