"""QTI import settles trailing points wording against the stored max_score (D8).

Synthetic free-text items through the real leaf mapping: an equal number
leaves the body, a differing number is recorded, look-alike prose stays.
"""

from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import_leaf_items import leaf_item
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.qti_import_mapping_support import (
    _document,
    _qti_item,
    _round_trip,
)

_VOLT = (
    "Pelle gör en fin volt, Sara gör en ful. Sätt poäng på Sara och Pelles volter. "
    "Använd mellan 3 poäng och 5 poäng."
)


class _NoAssets:
    def register(self, resource: ExamNetQtiImageResource) -> str:
        raise AssertionError("synthetic prompts carry no pictures")


def _imported(prompt: tuple[str, ...], max_score: int | float | None) -> NativeExamItem:
    source = replace(
        _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=1),
        prompt_lines=prompt,
        max_score=max_score,
    )
    item = leaf_item(source, sequence=1, assets=_NoAssets())
    assert item is not None
    return item


def _body_text(item: NativeExamItem) -> str:
    return "\n".join(item.plain_text_lines())


def test_trailing_label_leaves_the_body_and_keeps_the_source_record() -> None:
    item = _imported(("Beskriv processen. (2 p)",), 2)

    assert _body_text(item) == "Beskriv processen."
    assert item.points == 2
    assert item.leftover_points_text is None
    assert item.import_record is not None
    assert item.import_record.original_wording.question_text.endswith("(2 p)")


def test_trailing_points_line_leaves_whole() -> None:
    item = _imported(("Vad är svaret?", "Poäng: 2 poäng"), 2)

    assert _body_text(item) == "Vad är svaret?"
    assert item.points == 2
    assert item.leftover_points_text is None
    assert item.import_record is not None
    assert item.import_record.original_wording.question_text.endswith("Poäng: 2 poäng")


def test_differing_number_keeps_the_text_and_records_it() -> None:
    item = _imported(("Beskriv processen. (2 p)",), 3)

    assert _body_text(item) == "Beskriv processen. (2 p)"
    assert item.points == 3
    assert item.leftover_points_text == "(2 p)"
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()


def test_missing_score_keeps_the_text_and_records_nothing() -> None:
    item = _imported(("Beskriv processen. (2 p)",), None)

    assert _body_text(item) == "Beskriv processen. (2 p)"
    assert item.points is None
    assert item.leftover_points_text is None


def test_whole_stem_wording_stays_and_records_nothing() -> None:
    item = _imported(("(2 p)",), 2)

    assert _body_text(item) == "(2 p)"
    assert item.leftover_points_text is None


def test_volt_question_is_prose_for_every_score() -> None:
    for points in (5, 4):
        item = _imported((_VOLT,), points)

        assert _body_text(item) == _VOLT
        assert item.points == points
        assert item.leftover_points_text is None


def test_sentence_points_mention_stays() -> None:
    prompt = "Väljer eleven det får den 2 poäng."
    item = _imported((prompt,), 2)

    assert _body_text(item) == prompt
    assert item.leftover_points_text is None


def test_settled_item_still_exports_its_points() -> None:
    document = _document(
        (
            make_free_text_item().model_copy(
                update={"body": plain_body("Beskriv processen. (2 p)"), "points": 2}
            ),
        )
    )

    exported, container = _round_trip(document)

    assert exported[0].max_score == 2
    assert _body_text(container.document.items[0]) == "Beskriv processen."
    assert container.document.items[0].points == 2
