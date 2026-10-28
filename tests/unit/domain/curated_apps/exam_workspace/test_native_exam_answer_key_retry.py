"""The saved per-question answer-key retry (TASK-SKRIPT-40-04-26 D4, D5).

Purpose:
    Prove the retry flag is part of the saved question, defaults to ``none``
    for every new question, keeps suggest-all from filling a question whose
    AI key the teacher undid, and survives a type change and a re-conversion.
"""

import random

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_item_views,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import (
    change_item_type,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    replacement_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeAnswerKeyRetry,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_single_choice_item,
)


def _unkeyed_item(*, sequence: int, item_id: str, retry: NativeAnswerKeyRetry) -> NativeExamItem:
    item = make_single_choice_item(
        sequence=sequence,
        item_id=item_id,
        origin=NativeAnswerKeyOrigin.ABSENT,
        correct=(),
    ).model_copy(update={"answer_key_retry": retry})
    return item


class TestRetryField:
    def test_new_question_starts_with_no_retry(self) -> None:
        item = make_single_choice_item()

        assert item.answer_key_retry is NativeAnswerKeyRetry.NONE
        assert item.model_dump(mode="json")["answer_key_retry"] == "none"

    @pytest.mark.parametrize("retry", list(NativeAnswerKeyRetry))
    def test_retry_round_trips_through_json(self, retry: NativeAnswerKeyRetry) -> None:
        payload = {**make_single_choice_item().model_dump(mode="json")}
        payload["answer_key_retry"] = retry.value

        restored = NativeExamItem.model_validate(payload)

        assert restored.answer_key_retry is retry
        assert restored.model_dump(mode="json")["answer_key_retry"] == retry.value


class TestSuggestAllSelection:
    def test_skips_offered_and_used_retries_and_keeps_none(self) -> None:
        document = make_document(
            _unkeyed_item(sequence=1, item_id="item_001", retry=NativeAnswerKeyRetry.NONE),
            _unkeyed_item(sequence=2, item_id="item_002", retry=NativeAnswerKeyRetry.OFFERED),
            _unkeyed_item(sequence=3, item_id="item_003", retry=NativeAnswerKeyRetry.USED),
        )

        views = answer_key_item_views(document)

        assert [view.item_id for view in views] == ["item_001"]


class TestRetrySurvivesRebuilds:
    def test_type_change_keeps_a_spent_retry(self) -> None:
        document = make_document(
            _unkeyed_item(sequence=1, item_id="item_001", retry=NativeAnswerKeyRetry.USED)
        )

        result = change_item_type(
            document,
            item_id="item_001",
            target_kind=NativeExamItemKind.FREE_TEXT,
            rng=random.Random(0),
        )

        assert result.document.item_by_id("item_001").answer_key_retry is NativeAnswerKeyRetry.USED

    def test_re_conversion_keeps_a_spent_retry(self) -> None:
        original = _unkeyed_item(sequence=1, item_id="item_001", retry=NativeAnswerKeyRetry.USED)
        produced = make_single_choice_item(sequence=1, item_id="item_001")

        replacement = replacement_item(original=original, produced=produced)

        assert replacement.answer_key_retry is NativeAnswerKeyRetry.USED
