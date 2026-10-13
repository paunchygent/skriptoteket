"""Unit tests for the neutral answer-key item views (TASK-SKRIPT-39-04-01)."""

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyItemProposal,
    AnswerKeyViewKind,
    answer_key_item_views,
    proposal_from_model_content,
    suggestion_from_proposal,
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

pytestmark = pytest.mark.unit


def _suggestion(view, proposal: AnswerKeyItemProposal):
    return suggestion_from_proposal(
        view=view,
        proposal=proposal,
        provider_profile_id="profile",
        model="model",
        prompt_template_version="v1",
    )


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.DETERMINISTIC,
        confidence=0.9,
    )


def _choice_item(
    *,
    sequence: int,
    item_id: str,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.ABSENT,
    correct: tuple[str, ...] = (),
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(NativeParagraph(segments=(NativeTextSegment(text="Vilket är huvudordet?"),)),),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
        ),
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct),
        review=_review(),
    )


def _gap_item(*, sequence: int, item_id: str) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                segments=(
                    NativeTextSegment(text="Hon heter "),
                    NativeGapSegment(gap_id="gap_002"),
                    NativeTextSegment(text=" och bor i "),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text="."),
                )
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001"), NativeGap(gap_id="gap_002")),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        review=_review(),
    )


def _free_text_item(*, sequence: int, item_id: str) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(NativeParagraph(segments=(NativeTextSegment(text="Resonera."),)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=_review(),
    )


def _document(*items: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=tuple(items),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class TestViewSelection:
    def test_selects_only_keyed_items_with_absent_keys(self) -> None:
        document = _document(
            _choice_item(sequence=1, item_id="item_001"),
            _gap_item(sequence=2, item_id="item_002"),
            _choice_item(
                sequence=3,
                item_id="item_003",
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct=("choice_002",),
            ),
            _free_text_item(sequence=4, item_id="item_004"),
        )

        views = answer_key_item_views(document)

        assert [view.item_id for view in views] == ["item_001", "item_002"]

    def test_choice_view_maps_native_choice_ids_to_integers(self) -> None:
        views = answer_key_item_views(_document(_choice_item(sequence=1, item_id="item_001")))

        view = views[0]
        assert view.kind is AnswerKeyViewKind.CHOICE
        assert view.choices == ((1, "vägen"), (2, "eleverna"))
        assert view.stem_text == "Vilket är huvudordet?"
        assert view.gap_count == 0

    def test_gap_view_numbers_gaps_in_body_order(self) -> None:
        views = answer_key_item_views(_document(_gap_item(sequence=1, item_id="item_001")))

        view = views[0]
        assert view.kind is AnswerKeyViewKind.GAP_FILL
        assert view.gap_ids == ("gap_002", "gap_001")
        assert view.gap_count == 2
        assert view.cloze_text == "Hon heter [1] och bor i [2]."


class TestProposalValidation:
    def test_choice_decision_maps_back_to_native_choice_ids(self) -> None:
        view = answer_key_item_views(_document(_choice_item(sequence=1, item_id="item_001")))[0]

        proposal = proposal_from_model_content(view=view, content={"correct_alternative_ids": [2]})

        assert proposal is not None
        assert proposal.correct_choice_ids == ("choice_002",)

    def test_choice_decision_rejects_unknown_and_plural_single_choice(self) -> None:
        view = answer_key_item_views(_document(_choice_item(sequence=1, item_id="item_001")))[0]

        assert (
            proposal_from_model_content(view=view, content={"correct_alternative_ids": [9]}) is None
        )
        assert (
            proposal_from_model_content(view=view, content={"correct_alternative_ids": [1, 2]})
            is None
        )

    def test_gap_decision_binds_numbered_answers_to_body_order(self) -> None:
        view = answer_key_item_views(_document(_gap_item(sequence=1, item_id="item_001")))[0]

        proposal = proposal_from_model_content(view=view, content={"1": "Maja", "2": "Lund"})

        assert proposal is not None
        assert proposal.gap_accepted_values == (
            ("gap_002", ("Maja",)),
            ("gap_001", ("Lund",)),
        )

    def test_gap_decision_rejects_missing_empty_or_gap_id_values(self) -> None:
        view = answer_key_item_views(_document(_gap_item(sequence=1, item_id="item_001")))[0]

        assert proposal_from_model_content(view=view, content={"1": "Maja"}) is None
        assert proposal_from_model_content(view=view, content={"1": " ", "2": "Lund"}) is None
        assert proposal_from_model_content(view=view, content={"1": "gap_001", "2": "x"}) is None


class TestSuggestionFromProposal:
    def test_choice_suggestion_names_native_choice_ids(self) -> None:
        item = _choice_item(sequence=1, item_id="item_001")
        view = answer_key_item_views(_document(item))[0]
        proposal = proposal_from_model_content(view=view, content={"correct_alternative_ids": [2]})
        assert proposal is not None

        suggestion = _suggestion(view, proposal)

        assert suggestion.correct_choice_ids == ("choice_002",)
        assert suggestion.gap_accepted_values == ()
        assert suggestion.match_pairs == ()

    def test_gap_suggestion_carries_accepted_values_per_gap(self) -> None:
        item = _gap_item(sequence=1, item_id="item_001")
        view = answer_key_item_views(_document(item))[0]
        proposal = proposal_from_model_content(view=view, content={"1": "Maja", "2": "Lund"})
        assert proposal is not None

        suggestion = _suggestion(view, proposal)

        accepted = {entry.gap_id: entry.accepted_values for entry in suggestion.gap_accepted_values}
        assert accepted == {"gap_002": ("Maja",), "gap_001": ("Lund",)}
        assert suggestion.correct_choice_ids == ()
