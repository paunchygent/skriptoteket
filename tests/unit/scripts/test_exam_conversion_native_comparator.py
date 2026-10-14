"""The five-principle comparator judged on native documents replayed from recordings."""

from dataclasses import dataclass
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
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
    NativeItemReview,
    NativeItemReviewState,
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.scripts.exam_conversion_corpus_support import (
    STEMS,
    gold_exam,
    question_index,
    replayed,
    with_item,
)

_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_DIAGNOSTIC = "bf26_diagnostic_grammar_test_ht26_med_facit"
_WORD_BANK = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"


def _failed(comparison: ExamComparison, index: int) -> set[str]:
    return set(comparison.items[index].failed_principles())


def _compare(stem: str, document: NativeExamDocument | None = None) -> ExamComparison:
    recorded, chunks = replayed(stem)
    return compare_native_exam(gold_exam(stem), document or recorded, chunks)


def _text(item: NativeExamItem, text: str) -> NativeExamItem:
    paragraph = NativeParagraph(segments=(NativeTextSegment(text=text),))
    return item.model_copy(update={"body": (*item.body, paragraph)})


def _facit(item: GoldItem) -> str | None:
    if item.kind not in ("free_text", "review"):
        return None
    lines = [line for note in item.notes for line in note.split("\n") if ":" in line]
    return lines[-1].rsplit(":", 1)[1].strip() if lines else None


@dataclass(frozen=True)
class _LeakHit:
    """One deliberate facit leak: an open gold question, the converted free-text item whose
    wording pairs with it, and that item with the facit appended."""

    stem: str
    gold_index: int
    item_index: int
    leaked: NativeExamItem
    baseline: ExamComparison
    comparison: ExamComparison


def _facit_leak_hits() -> list[_LeakHit]:
    """Per open gold question that keeps a facit, the first converted free-text item where
    appending that facit makes the comparator report leakage on that question."""
    hits: list[_LeakHit] = []
    for stem in STEMS:
        recorded, _ = replayed(stem)
        baseline = _compare(stem)
        free_text = [
            (index, item)
            for index, item in enumerate(recorded.items)
            if item.kind is NativeExamItemKind.FREE_TEXT
            and item.review.parse_origin is NativeParseOrigin.LLM_PARSED
        ]
        for gold_index, question in enumerate(gold_exam(stem).questions):
            facit = _facit(question)
            if facit is None or "no_answer_leakage" in _failed(baseline, gold_index):
                continue
            for item_index, item in free_text:
                leaked = _text(item, facit)
                comparison = _compare(stem, with_item(recorded, item_index, leaked))
                if "no_answer_leakage" in _failed(comparison, gold_index):
                    hits.append(
                        _LeakHit(stem, gold_index, item_index, leaked, baseline, comparison)
                    )
                    break
    return hits


def test_the_teachers_facit_appended_to_an_open_native_question_leaks():
    hits = _facit_leak_hits()
    # Only exams with an open question whose gold keeps a teacher's facit can leak it.
    with_facit = {stem for stem in STEMS if any(_facit(q) for q in gold_exam(stem).questions)}
    assert with_facit
    assert {hit.stem for hit in hits} >= with_facit
    for hit in hits:
        assert "no_answer_leakage" not in _failed(hit.baseline, hit.gold_index), hit.stem
        assert "no_answer_leakage" in _failed(hit.comparison, hit.gold_index), hit.stem


def _leaked_as(hit: _LeakHit, review: NativeItemReview) -> set[str]:
    """The failed principles of the hit's gold question when its leaked item carries `review`."""
    recorded, _ = replayed(hit.stem)
    reviewed = hit.leaked.model_copy(update={"review": review})
    return _failed(
        _compare(hit.stem, with_item(recorded, hit.item_index, reviewed)), hit.gold_index
    )


def test_a_review_item_built_from_source_never_leaks_but_a_converted_one_under_review_does():
    hits = _facit_leak_hits()
    assert hits
    from_source = NativeItemReview(
        state=NativeItemReviewState.REVIEW_REQUIRED,
        parse_origin=NativeParseOrigin.DETERMINISTIC,
        reasons=("Frågan behöver granskas.",),
    )
    converted_under_review = NativeItemReview(
        state=NativeItemReviewState.REVIEW_REQUIRED,
        parse_origin=NativeParseOrigin.LLM_PARSED,
        reasons=("Frågan behöver granskas.",),
    )
    for hit in hits:
        assert "no_answer_leakage" in _failed(hit.comparison, hit.gold_index), hit.stem
        assert "no_answer_leakage" not in _leaked_as(hit, from_source), hit.stem
        assert "no_answer_leakage" in _leaked_as(hit, converted_under_review), hit.stem


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


def test_parents_regrouped_with_their_instruction_kept_still_pass():
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
        assert all(comparison.items[i].passed for i in _positions(recorded, parent)), stem


def test_a_parent_instruction_moved_onto_every_child_passes():
    cases = _clean_parents()
    assert len(cases) >= 3
    for stem, recorded, parent, _ in cases:
        items = list(recorded.items)
        for i in _positions(recorded, parent):
            items[i] = _text(items[i], body_plain_text(parent.instruction))
        moved = _replace_parent(
            recorded.model_copy(update={"items": tuple(items)}),
            parent,
            parent.model_copy(
                update={
                    "instruction": (NativeParagraph(segments=(NativeTextSegment(text="Svara."),)),)
                }
            ),
        )
        comparison = _compare(stem, moved)
        assert all(comparison.items[i].passed for i in _positions(recorded, parent)), stem


def _failing_children(
    cases: list[tuple[str, NativeExamDocument, NativeExamParent, ExamComparison]],
    change,
) -> list[tuple[str, int, set[str]]]:
    """Per case, the children that fail once `change` rewrites the document."""
    failing = []
    for stem, recorded, parent, _ in cases:
        comparison = _compare(stem, change(recorded, parent))
        for i in _positions(recorded, parent):
            if failed := _failed(comparison, i):
                failing.append((stem, i, failed))
    return failing


def test_a_document_without_its_parents_loses_instruction_words_only():
    cases = _clean_parents()
    assert len(cases) >= 3
    failing = _failing_children(
        cases, lambda recorded, _: recorded.model_copy(update={"parents": ()})
    )
    assert len(failing) >= 3
    assert all(failed == {"content_present"} for *_, failed in failing)


def test_dropping_the_parent_instruction_loses_instruction_words_only():
    cases = _clean_parents()
    assert len(cases) >= 3
    failing = _failing_children(
        cases,
        lambda recorded, parent: _replace_parent(
            recorded,
            parent,
            parent.model_copy(
                update={
                    "instruction": (NativeParagraph(segments=(NativeTextSegment(text="Svara."),)),)
                }
            ),
        ),
    )
    assert len(failing) >= 3
    assert all(failed == {"content_present"} for *_, failed in failing)


def test_a_childs_answer_disclosed_in_its_parent_instruction_leaks():
    recorded, _ = replayed(_DIAGNOSTIC)
    child = next(item for item in recorded.items if item.gaps and recorded.parent_of(item.item_id))
    parent = recorded.parent_of(child.item_id)
    assert parent is not None
    index = recorded.items.index(child)
    answer = child.gaps[0].accepted_values[0]
    assert answer == "play"
    assert answer not in body_plain_text(parent.instruction).lower()
    assert _compare(_DIAGNOSTIC).items[index].passed

    disclosed = parent.model_copy(
        update={
            "instruction": (
                *parent.instruction,
                NativeParagraph(segments=(NativeTextSegment(text=answer),)),
            )
        }
    )
    mutated = _replace_parent(recorded, parent, disclosed)
    assert mutated.items is recorded.items
    comparison = _compare(_DIAGNOSTIC, mutated)
    assert _failed(comparison, index) == {"no_answer_leakage"}


@pytest.mark.parametrize("stem", [_DIAGNOSTIC, _WORD_BANK])
def test_unchanged_native_parent_instructions_and_word_banks_do_not_leak(stem: str):
    recorded, _ = replayed(stem)
    assert recorded.parents
    if stem == _WORD_BANK:
        assert any(
            value.lower() in body_plain_text(parent.instruction).lower()
            for parent in recorded.parents
            for index in _positions(recorded, parent)
            for gap in recorded.items[index].gaps
            for value in gap.accepted_values
        )
    baseline = _compare(stem)
    for parent in recorded.parents:
        for index in _positions(recorded, parent):
            assert "no_answer_leakage" not in _failed(baseline, index)


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


def test_native_matching_lists_in_another_order_pass():
    single, item, _, rights = _matching_case()
    reordered = _native_matching(item, [rights[1], rights[0], *rights[2:]])
    comparison = compare_native_exam(
        single, _document(reordered).model_copy(update={"title": single.title})
    )
    assert comparison.passed


@pytest.mark.parametrize("dropped", ["left", "right"])
def test_native_matching_with_a_lost_entry_fails_content(dropped: str):
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
    assert "content_present" in _failed(compare_native_exam(single, document), 0)


def test_native_matching_with_an_extra_distractor_entry_passes():
    single, item, _, rights = _matching_case()
    native = _native_matching(item, rights)
    distractor = NativeMatchRight(right_id="right_099", text="an entry the source never lists")
    extended = native.model_copy(update={"match_right": (*native.match_right, distractor)})
    document = _document(extended).model_copy(update={"title": single.title})
    assert compare_native_exam(single, document).passed
