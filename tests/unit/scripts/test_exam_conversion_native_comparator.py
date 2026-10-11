"""The principle comparator judged on native documents replayed from the recorded conversions."""

from uuid import uuid4

import pytest

from scripts.exam_conversion_eval.compare import (
    ExamComparison,
    compare_native_exam,
)
from scripts.exam_conversion_eval.gold import GoldExam, GoldItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
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
from tests.unit.scripts.exam_conversion_corpus_support import (
    STEMS,
    gold_exam,
    question_index,
    replayed,
    with_item,
)

_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"


def _failed(comparison: ExamComparison, index: int) -> set[str]:
    return set(comparison.items[index].failed_principles())


def _compare(stem: str, document: NativeExamDocument | None = None) -> ExamComparison:
    recorded, chunks = replayed(stem)
    return compare_native_exam(gold_exam(stem), document or recorded, chunks)


def _text(item: NativeExamItem, text: str) -> NativeExamItem:
    paragraph = NativeParagraph(segments=(NativeTextSegment(text=text),))
    return item.model_copy(update={"body": (*item.body, paragraph)})


def _gap_moved_next_to_the_other_gap(item: NativeExamItem) -> NativeExamItem | None:
    """The item with the text between its first and last gap moved after them, or None."""
    for at, paragraph in enumerate(item.body):
        segments = paragraph.segments
        gaps = [i for i, seg in enumerate(segments) if isinstance(seg, NativeGapSegment)]
        if len(gaps) >= 2 and any(
            isinstance(seg, NativeTextSegment) and seg.text.strip()
            for seg in segments[gaps[0] + 1 : gaps[-1]]
        ):
            leading = list(segments[: gaps[0]])
            rest = list(segments[gaps[0] :])
            moved = (
                *leading,
                *(seg for seg in rest if isinstance(seg, NativeGapSegment)),
                *(seg for seg in rest if isinstance(seg, NativeTextSegment)),
            )
            body = list(item.body)
            body[at] = paragraph.model_copy(update={"segments": moved})
            return item.model_copy(update={"body": tuple(body)})
    return None


def _facit(item: GoldItem) -> str | None:
    if item.kind not in ("free_text", "review"):
        return None
    lines = [line for note in item.notes for line in note.split("\n") if ":" in line]
    return lines[-1].rsplit(":", 1)[1].strip() if lines else None


def _mutations(mutate, principle: str) -> list[tuple[str, int, ExamComparison, ExamComparison]]:
    """Per exam, the first item that meets the principle and the mutation applies to.

    Each hit is judged before and after the mutation.
    """
    hits = []
    for stem in STEMS:
        recorded, _ = replayed(stem)
        baseline = _compare(stem)
        for index, item in enumerate(recorded.items):
            if principle in _failed(baseline, index):
                continue
            mutated = mutate(stem, index, item)
            if mutated is not None:
                hits.append(
                    (stem, index, baseline, _compare(stem, with_item(recorded, index, mutated)))
                )
                break
    return hits


def test_a_gap_moved_next_to_the_other_gap_fails_response_slots():
    hits = _mutations(
        lambda stem, index, item: _gap_moved_next_to_the_other_gap(item), "response_slots"
    )
    assert len(hits) >= 2
    for stem, index, baseline, mutated in hits:
        assert "response_slots" not in _failed(baseline, index), stem
        assert "response_slots" in _failed(mutated, index), stem
        assert "content_present" not in _failed(mutated, index) - _failed(baseline, index), stem


def test_a_duplicated_native_choice_fails_response_slots():
    def duplicate(stem: str, index: int, item: NativeExamItem) -> NativeExamItem | None:
        if not item.choices:
            return None
        extra = NativeChoice(
            choice_id=f"choice_{len(item.choices) + 1:03d}", text=item.choices[0].text
        )
        return NativeExamItem.model_validate(
            {**item.model_dump(), "choices": (*item.choices, extra)}
        )

    hits = _mutations(duplicate, "response_slots")
    assert len(hits) >= 5
    for stem, index, baseline, mutated in hits:
        assert "response_slots" not in _failed(baseline, index), stem
        assert "response_slots" in _failed(mutated, index), stem


def test_the_teachers_facit_appended_to_an_open_native_question_leaks():
    def leak(stem: str, index: int, item: NativeExamItem) -> NativeExamItem | None:
        gold = gold_exam(stem)
        if len(gold.questions) != len(replayed(stem)[0].items):
            return None
        facit = _facit(gold.questions[index])
        if facit is None or item.kind is not NativeExamItemKind.FREE_TEXT:
            return None
        return _text(item, facit)

    hits = _mutations(leak, "no_answer_leakage")
    assert {stem for stem, *_ in hits} >= {s for s in STEMS if s.startswith("svenska_2")}
    for stem, index, baseline, mutated in hits:
        assert "no_answer_leakage" not in _failed(baseline, index), stem
        assert "no_answer_leakage" in _failed(mutated, index), stem


def test_a_question_number_on_a_titled_body_fails_labels():
    def number(stem: str, index: int, item: NativeExamItem) -> NativeExamItem | None:
        first = item.body[0].segments[0]
        if not item.title or not isinstance(first, NativeTextSegment):
            return None
        numbered = item.body[0].model_copy(
            update={"segments": (first.model_copy(update={"text": f"1. {first.text}"}),)}
        )
        return item.model_copy(update={"body": (numbered, *item.body[1:])})

    hits = _mutations(number, "no_platform_labels")
    assert len(hits) >= 2
    for stem, index, baseline, mutated in hits:
        assert "no_platform_labels" not in _failed(baseline, index), stem
        assert "no_platform_labels" in _failed(mutated, index), stem


def _clean_parents() -> list[tuple[str, NativeExamDocument, NativeExamParent, ExamComparison]]:
    """Recorded parents whose children all meet every principle."""
    found = []
    for stem in STEMS:
        recorded, _ = replayed(stem)
        baseline = _compare(stem)
        position = {item.item_id: i for i, item in enumerate(recorded.items)}
        for parent in recorded.parents:
            if len(parent.item_ids) >= 2 and all(
                baseline.items[position[item_id]].passed for item_id in parent.item_ids
            ):
                found.append((stem, recorded, parent, baseline))
    return found


def _positions(document: NativeExamDocument, parent: NativeExamParent) -> list[int]:
    wanted = set(parent.item_ids)
    return [i for i, item in enumerate(document.items) if item.item_id in wanted]


def _replace_parent(
    document: NativeExamDocument, parent: NativeExamParent, *replacements: NativeExamParent
) -> NativeExamDocument:
    parents = [r for p in document.parents for r in (replacements if p is parent else (p,))]
    return document.model_copy(update={"parents": tuple(parents)})


def test_a_child_moved_out_of_its_parent_fails_segmentation():
    cases = _clean_parents()
    assert len(cases) >= 3
    for stem, recorded, parent, _ in cases:
        shorter = parent.model_copy(update={"item_ids": parent.item_ids[:-1]})
        comparison = _compare(stem, _replace_parent(recorded, parent, shorter))
        positions = _positions(recorded, parent)
        assert {m.reason for m in comparison.items[positions[-1]].mismatches} >= {
            "parent_membership"
        }, stem
        assert all("segmentation" in _failed(comparison, i) for i in positions), stem


def test_a_parent_that_splits_a_gold_parent_fails_segmentation():
    cases = _clean_parents()
    assert len(cases) >= 3
    for stem, recorded, parent, _ in cases:
        first = parent.model_copy(
            update={"parent_id": "parent_901", "item_ids": parent.item_ids[:1]}
        )
        rest = parent.model_copy(
            update={"parent_id": "parent_902", "item_ids": parent.item_ids[1:]}
        )
        comparison = _compare(stem, _replace_parent(recorded, parent, first, rest))
        for i in _positions(recorded, parent):
            assert "parent_membership" in {m.reason for m in comparison.items[i].mismatches}, stem


def test_a_document_without_its_parents_fails_segmentation_and_loses_the_instruction():
    cases = _clean_parents()
    assert len(cases) >= 3
    for stem, recorded, parent, _ in cases:
        comparison = _compare(stem, recorded.model_copy(update={"parents": ()}))
        for i in _positions(recorded, parent):
            assert {"segmentation", "content_present"} <= _failed(comparison, i), stem


def test_dropping_the_parent_instruction_fails_content_for_every_child():
    cases = _clean_parents()
    assert len(cases) >= 3
    for stem, recorded, parent, _ in cases:
        dropped = parent.model_copy(update={"instruction": ("Svara på frågorna.",)})
        comparison = _compare(stem, _replace_parent(recorded, parent, dropped))
        for i in _positions(recorded, parent):
            assert "content_present" in _failed(comparison, i), stem
            assert "segmentation" not in _failed(comparison, i), stem


def _single(exam: GoldExam, item: GoldItem) -> GoldExam:
    return GoldExam.model_validate({**exam.model_dump(), "items": [item.model_dump()]})


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE, parse_origin=NativeParseOrigin.LLM_PARSED
    )


def _table_cells(item: GoldItem) -> tuple[list[str], list[str]]:
    rows = [line.split(" | ") for line in item.prompt.split("\n") if " | " in line]
    return [row[0].split(". ", 1)[1] for row in rows], [row[1].split(". ", 1)[1] for row in rows]


def _native_matching(item: GoldItem, rights: list[str]) -> NativeExamItem:
    lefts, _ = _table_cells(item)
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


def _document(item: NativeExamItem, *, validate: bool = True) -> NativeExamDocument:
    build = NativeExamDocument if validate else NativeExamDocument.model_construct
    return build(
        document_id=uuid4(),
        revision=1,
        title="t",
        items=(item,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _matching_case() -> tuple[GoldExam, GoldItem, NativeExamItem, list[str]]:
    exam = gold_exam(_ENGLISH)
    item = exam.questions[question_index(exam, "Vocabulary Matching, Question 1")]
    _, rights = _table_cells(item)
    return _single(exam, item), item, _native_matching(item, rights), rights


def test_native_matching_with_lists_in_table_order_passes_and_a_wrong_pair_fails():
    single, _, native, _ = _matching_case()
    title = single.title
    assert compare_native_exam(single, _document(native).model_copy(update={"title": title})).passed
    key = native.answer_key
    swapped = (
        key.match_pairs[0].model_copy(update={"right_id": key.match_pairs[1].right_id}),
        key.match_pairs[1].model_copy(update={"right_id": key.match_pairs[0].right_id}),
        *key.match_pairs[2:],
    )
    wrong = native.model_copy(
        update={"answer_key": key.model_copy(update={"match_pairs": swapped})}
    )
    comparison = compare_native_exam(single, _document(wrong).model_copy(update={"title": title}))
    assert _failed(comparison, 0) == {"scoring"}


def test_native_matching_lists_in_another_order_fail_response_slots():
    single, item, _, rights = _matching_case()
    reordered = _native_matching(item, [rights[1], rights[0], *rights[2:]])
    comparison = compare_native_exam(
        single, _document(reordered).model_copy(update={"title": single.title})
    )
    assert _failed(comparison, 0) == {"response_slots"}


@pytest.mark.parametrize("dropped", ["left", "right"])
def test_native_matching_with_a_lost_entry_fails_slots(dropped: str):
    single, _, native, _ = _matching_case()
    match_left = native.match_left[:-1] if dropped == "left" else native.match_left
    match_right = native.match_right[:-1] if dropped == "right" else native.match_right
    kept_left = {entry.left_id for entry in match_left}
    kept_right = {entry.right_id for entry in match_right}
    pairs = tuple(
        pair
        for pair in native.answer_key.match_pairs
        if pair.left_id in kept_left and pair.right_id in kept_right
    )
    key = native.answer_key.model_construct(**{**dict(native.answer_key), "match_pairs": pairs})
    shortened = native.model_construct(
        **{**dict(native), "match_left": match_left, "match_right": match_right, "answer_key": key}
    )
    document = _document(shortened, validate=False).model_copy(update={"title": single.title})
    assert "response_slots" in _failed(compare_native_exam(single, document), 0)


def test_native_matching_with_an_extra_distractor_entry_fails_response_slots():
    single, item, _, rights = _matching_case()
    native = _native_matching(item, rights)
    distractor = NativeMatchRight(right_id="right_099", text="an entry the source never lists")
    extended = native.model_copy(update={"match_right": (*native.match_right, distractor)})
    document = _document(extended).model_copy(update={"title": single.title})
    assert "response_slots" in _failed(compare_native_exam(single, document), 0)
