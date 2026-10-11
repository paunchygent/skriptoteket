"""The principle comparator judged on real gold items and conversions that break one principle."""

from pathlib import Path
from uuid import uuid4

import pytest

from scripts.exam_conversion_eval.compare import (
    PRINCIPLES,
    ExamComparison,
    compare_exam,
    compare_native_exam,
)
from scripts.exam_conversion_eval.gold import GoldExam, GoldGap, GoldItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)

_GOLD = Path("tests/fixtures/exam_conversion/docx_corpus/gold")


def _gold(stem: str) -> GoldExam:
    return GoldExam.model_validate_json((_GOLD / f"{stem}.json").read_text())


def _with_item(exam: GoldExam, index: int, **update: object) -> tuple[GoldItem, ...]:
    items = list(exam.items)
    items[index] = items[index].model_copy(update=update)
    return tuple(items)


def _failed(comparison: ExamComparison, index: int) -> set[str]:
    return set(comparison.items[index].failed_principles())


def _english() -> GoldExam:
    return _gold("bf26_english_1_unit_test_kap_1_2_med_facit")


def _index(exam: GoldExam, label: str) -> int:
    return next(i for i, item in enumerate(exam.items) if item.source_label == label)


def test_gold_passes_every_principle_against_itself():
    for path in sorted(_GOLD.glob("*.json")):
        comparison = compare_exam(_gold(path.stem), _gold(path.stem).items)
        assert comparison.passed, path.stem
        assert set(comparison.failures_by_principle()) == set(PRINCIPLES)


def test_answer_written_into_the_prompt_leaks_and_loses_the_slot():
    exam = _english()
    index = _index(exam, "Grammar and Corrections, Question 7")
    item = exam.items[index]
    answer = item.gaps[0].accepted_values[0]
    filled = item.prompt.replace("[___]", answer)
    comparison = compare_exam(exam, _with_item(exam, index, prompt=filled, gaps=()))
    assert _failed(comparison, index) == {
        "no_answer_leakage",
        "response_slots",
        "scoring",
        "content_present",
    }


def test_typographic_facit_without_its_keyboard_form_fails_scoring():
    exam = _english()
    index = _index(exam, "Grammar and Corrections, Question 7")
    curly = tuple(v for v in exam.items[index].gaps[0].accepted_values if "’" in v)
    assert curly
    comparison = compare_exam(exam, _with_item(exam, index, gaps=(GoldGap(accepted_values=curly),)))
    assert _failed(comparison, index) == {"scoring"}


def test_wording_differences_the_principles_ignore_pass():
    exam = _gold("svenska_2_grammatik_omprov_variant_2_med_facit")
    item = exam.items[3]
    restyled = item.prompt.upper().replace("\n", " ").replace(".", "")
    comparison = compare_exam(exam, _with_item(exam, 3, prompt=restyled))
    assert comparison.items[3].passed


def test_a_dropped_instruction_line_fails_content():
    exam = _gold("svenska_2_grammatik_omprov_variant_2_med_facit")
    item = exam.items[3]
    shortened = "\n".join(line for line in item.prompt.split("\n")[1:])
    comparison = compare_exam(exam, _with_item(exam, 3, prompt=shortened))
    assert _failed(comparison, 3) == {"content_present"}


def test_defined_abbreviation_term_and_slash_parts_are_admitted_extras():
    exam = _gold("svenska_2_grammatik_omprov_variant_2_med_facit")
    item = exam.items[3]
    # Each gold gap holds a term and its defined abbreviation; keep only the abbreviation and
    # add back the term and slash parts as model extras in another order.
    reordered = tuple(
        GoldGap(accepted_values=tuple(reversed(g.accepted_values))) for g in item.gaps
    )
    comparison = compare_exam(exam, _with_item(exam, 3, gaps=reordered))
    assert comparison.items[3].passed


def test_another_gaps_gold_answer_fails_and_a_missing_answer_fails():
    exam = _gold("svenska_2_grammatik_omprov_variant_2_med_facit")
    item = exam.items[3]
    first, second, *rest = item.gaps
    crossed = GoldGap(accepted_values=(*first.accepted_values, second.accepted_values[0]))
    missing = GoldGap(accepted_values=second.accepted_values[1:])
    comparison = compare_exam(exam, _with_item(exam, 3, gaps=(crossed, missing, *rest)))
    reasons = {m.reason for m in comparison.items[3].mismatches}
    assert reasons == {"gap 1 accepts extra", "gap 2 misses"}


def test_text_of_the_neighbouring_question_fails_segmentation():
    """A live round copied question 7's wording into question 8."""
    exam = _gold("chapter_4_poetry_and_lyrics_quiz_med_facit")
    seventh = _index(exam, "Part 1, Question 7")
    comparison = compare_exam(
        exam, _with_item(exam, seventh + 1, prompt=exam.items[seventh].prompt)
    )
    assert _failed(comparison, seventh + 1) == {"segmentation", "content_present"}
    assert comparison.items[seventh].passed


def test_option_letters_question_numbers_points_and_blanks_fail_labels():
    exam = _gold("chapter_4_poetry_and_lyrics_quiz_med_facit")
    index = _index(exam, "Part 1, Question 7")
    item = exam.items[index]
    lettered = tuple(f"{chr(65 + i)}. {choice}" for i, choice in enumerate(item.choices))
    for update in (
        {"choices": lettered, "correct_choices": (lettered[item.choices.index("speaker")],)},
        {"prompt": f"7. {item.prompt}"},
        {"prompt": f"{item.prompt} (1 point)"},
        {"prompt": f"{item.prompt} ________"},
    ):
        comparison = compare_exam(exam, _with_item(exam, index, **update))
        assert "no_platform_labels" in _failed(comparison, index), update


def test_point_and_kind_differences_fail_their_principles():
    exam = _english()
    index = _index(exam, "Vocabulary Matching, Question 1")
    comparison = compare_exam(exam, _with_item(exam, index, points=1))
    assert _failed(comparison, index) == {"points"}
    item = exam.items[index]
    as_text = _with_item(exam, index, kind="free_text", pairs=())
    assert _failed(compare_exam(exam, as_text), index) == {
        "response_kind",
        "response_slots",
        "scoring",
    }
    assert item.kind == "matching"


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE, parse_origin=NativeParseOrigin.LLM_PARSED
    )


def _native_matching(item: GoldItem, rights: tuple[str, ...]) -> NativeExamItem:
    lefts = tuple(pair.left for pair in item.pairs)
    left = tuple(NativeMatchLeft(left_id=f"left_{i:03d}", text=t) for i, t in enumerate(lefts, 1))
    right = tuple(
        NativeMatchRight(right_id=f"right_{i:03d}", text=t) for i, t in enumerate(rights, 1)
    )
    right_ids = {entry.text: entry.right_id for entry in right}
    pairs = tuple(
        NativeMatchPair(left_id=entry.left_id, right_id=right_ids[pair.right])
        for entry, pair in zip(left, item.pairs, strict=True)
    )
    instructions = [line for line in item.prompt.split("\n") if " | " not in line]
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.MATCHING,
        body=tuple(
            NativeParagraph(segments=(NativeTextSegment(text=line),)) for line in instructions
        ),
        points=item.points,
        match_left=left,
        match_right=right,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED, match_pairs=pairs),
        review=_review(),
    )


def _document(items: tuple[NativeExamItem, ...], *, validate: bool = True) -> NativeExamDocument:
    build = NativeExamDocument if validate else NativeExamDocument.model_construct
    return build(
        document_id=uuid4(),
        revision=1,
        title="t",
        items=tuple(
            item.model_copy(update={"item_id": f"item_{i:03d}", "sequence": i})
            for i, item in enumerate(items, 1)
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def test_native_matching_item_with_lists_instead_of_table_text_passes_and_wrong_pair_fails():
    exam = _english()
    index = _index(exam, "Vocabulary Matching, Question 1")
    gold_item = exam.items[index]
    rights = tuple(sorted(pair.right for pair in gold_item.pairs))
    single = GoldExam.model_validate({**exam.model_dump(), "items": [gold_item.model_dump()]})
    native = _native_matching(gold_item, rights)
    assert compare_native_exam(single, _document((native,))).passed

    key = native.answer_key
    swapped = (
        key.match_pairs[0].model_copy(update={"right_id": key.match_pairs[1].right_id}),
        key.match_pairs[1].model_copy(update={"right_id": key.match_pairs[0].right_id}),
        *key.match_pairs[2:],
    )
    wrong = native.model_copy(
        update={"answer_key": key.model_copy(update={"match_pairs": swapped})}
    )
    comparison = compare_native_exam(single, _document((wrong,)))
    assert _failed(comparison, 0) == {"scoring"}


@pytest.mark.parametrize("dropped", ["left", "right"])
def test_native_matching_with_a_lost_entry_fails_slots(dropped: str):
    exam = _english()
    gold_item = exam.items[_index(exam, "Vocabulary Matching, Question 2")]
    single = GoldExam.model_validate({**exam.model_dump(), "items": [gold_item.model_dump()]})
    native = _native_matching(gold_item, tuple(pair.right for pair in gold_item.pairs))
    match_left = native.match_left[:-1] if dropped == "left" else native.match_left
    match_right = native.match_right[:-1] if dropped == "right" else native.match_right
    lists = {"match_left": match_left, "match_right": match_right}
    kept_left = {entry.left_id for entry in match_left}
    kept_right = {entry.right_id for entry in match_right}
    pairs = tuple(
        pair
        for pair in native.answer_key.match_pairs
        if pair.left_id in kept_left and pair.right_id in kept_right
    )
    key = native.answer_key.model_construct(**{**dict(native.answer_key), "match_pairs": pairs})
    shortened = native.model_construct(**{**dict(native), **lists, "answer_key": key})
    comparison = compare_native_exam(single, _document((shortened,), validate=False))
    assert "response_slots" in _failed(comparison, 0)
