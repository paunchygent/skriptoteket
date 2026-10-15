"""The five-principle comparator judged on real gold questions and teacher-acceptable variants."""

import re

import pytest

from scripts.exam_conversion_eval.compare import (
    PRINCIPLES,
    ExamComparison,
    compare_exam,
)
from scripts.exam_conversion_eval.gold import GoldExam, GoldGap, GoldItem, GoldParent
from tests.unit.scripts.exam_conversion_corpus_support import (
    AUTHORED_STEM,
    STEMS,
    gold_exam,
    mutated_items,
    question_index,
)

_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_SVENSKA = "svenska_2_grammatik_omprov_variant_2_med_facit"
_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_DIAGNOSTIC = "bf26_diagnostic_grammar_test_ht26_med_facit"
_WORD_BANK = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"


def _failed(comparison: ExamComparison, index: int) -> set[str]:
    return set(comparison.items[index].failed_principles())


def _first(exam: GoldExam, wanted) -> int | None:
    return next((i for i, item in enumerate(exam.questions) if wanted(item)), None)


def _cases(wanted) -> list[tuple[str, int]]:
    """The first question per exam that the predicate selects."""
    cases = []
    for stem in STEMS:
        index = _first(gold_exam(stem), wanted)
        if index is not None:
            cases.append((stem, index))
    return cases


def _multiline_free_text(item: GoldItem) -> bool:
    return item.kind == "free_text" and "\n" in item.prompt


def _text_between_gaps(item: GoldItem) -> bool:
    return any(
        line.count("[___]") >= 2 and line.split("[___]")[1].strip()
        for line in item.prompt.split("\n")
    )


def _facit(item: GoldItem) -> str | None:
    """The teacher's facit for an open question: the text after the last colon of a note line."""
    if item.kind not in ("free_text", "review"):
        return None
    lines = [line for note in item.notes for line in note.split("\n") if ":" in line]
    return lines[-1].rsplit(":", 1)[1].strip() if lines else None


def test_gold_passes_every_principle_against_itself():
    for stem in STEMS:
        exam = gold_exam(stem)
        comparison = compare_exam(exam, exam.items)
        assert comparison.passed, stem
        assert comparison.title.passed
        assert set(comparison.failures_by_principle()) == set(PRINCIPLES)
        assert len(comparison.items) == len(exam.questions)


def test_parent_children_are_reported_under_parent_and_child_label():
    exam = gold_exam(_ENGLISH)
    parent = next(item for item in exam.items if isinstance(item, GoldParent))
    labels = [item.source_label for item in compare_exam(exam, exam.items).items]
    assert f"{parent.source_label} / {parent.children[0].source_label}" in labels


def test_answer_written_into_the_prompt_leaks_and_loses_the_key():
    exam = gold_exam(_ENGLISH)
    index = question_index(exam, "Grammar and Corrections, Question 7")
    item = exam.questions[index]
    answer = item.gaps[0].accepted_values[0]
    filled = item.prompt.replace("[___]", answer)
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=filled, gaps=()))
    assert _failed(comparison, index) == {"no_answer_leakage", "scoring"}


def test_typographic_facit_without_its_keyboard_form_fails_scoring():
    exam = gold_exam(_ENGLISH)
    index = question_index(exam, "Grammar and Corrections, Question 7")
    curly = tuple(v for v in exam.questions[index].gaps[0].accepted_values if "’" in v)
    assert curly
    gaps = (GoldGap(accepted_values=curly),)
    comparison = compare_exam(exam, mutated_items(exam, index, gaps=gaps))
    assert _failed(comparison, index) == {"scoring"}


def test_wording_differences_the_principles_ignore_pass():
    exam = gold_exam(_SVENSKA)
    restyled = exam.questions[3].prompt.upper().replace("\n", " ").replace(".", "")
    comparison = compare_exam(exam, mutated_items(exam, 3, prompt=restyled))
    assert comparison.items[3].passed


def test_a_dropped_instruction_line_fails_content():
    exam = gold_exam(_SVENSKA)
    shortened = "\n".join(exam.questions[3].prompt.split("\n")[1:])
    comparison = compare_exam(exam, mutated_items(exam, 3, prompt=shortened))
    assert _failed(comparison, 3) == {"content_present"}


def test_defined_abbreviation_term_and_slash_parts_are_admitted_extras():
    exam = gold_exam(_SVENSKA)
    item = exam.questions[3]
    # Each gold gap holds a term and its defined abbreviation; reverse their order.
    reordered = tuple(
        GoldGap(accepted_values=tuple(reversed(g.accepted_values))) for g in item.gaps
    )
    comparison = compare_exam(exam, mutated_items(exam, 3, gaps=reordered))
    assert comparison.items[3].passed


def test_another_gaps_gold_answer_fails_and_a_missing_answer_fails():
    exam = gold_exam(_SVENSKA)
    first, second, *rest = exam.questions[3].gaps
    crossed = GoldGap(accepted_values=(*first.accepted_values, second.accepted_values[0]))
    missing = GoldGap(accepted_values=second.accepted_values[1:])
    gaps = (crossed, missing, *rest)
    comparison = compare_exam(exam, mutated_items(exam, 3, gaps=gaps))
    reasons = {m.reason for m in comparison.items[3].mismatches}
    assert reasons == {"gap 1 accepts extra", "gap 2 misses"}


def test_text_of_the_neighbouring_question_in_place_of_the_prompt_loses_the_wording():
    """A live round copied question 7's wording into question 8."""
    exam = gold_exam(_POETRY)
    seventh = question_index(exam, "Part 1, Question 7")
    prompt = exam.questions[seventh].prompt
    comparison = compare_exam(exam, mutated_items(exam, seventh + 1, prompt=prompt))
    assert _failed(comparison, seventh + 1) == {"content_present"}
    assert comparison.items[seventh].passed


def test_foreign_wording_beside_the_whole_gold_wording_passes():
    exam = gold_exam(_POETRY)
    seventh = question_index(exam, "Part 1, Question 7")
    own = exam.questions[seventh + 1].prompt
    foreign = exam.questions[seventh].prompt.split("\n")[0]
    comparison = compare_exam(exam, mutated_items(exam, seventh + 1, prompt=f"{own}\n{foreign}"))
    assert comparison.items[seventh + 1].passed


def test_option_letters_question_numbers_points_and_blanks_are_not_judged():
    exam = gold_exam(_POETRY)
    index = question_index(exam, "Part 1, Question 7")
    item = exam.questions[index]
    for update in (
        {"prompt": f"7. {item.prompt}"},
        {"prompt": f"{item.prompt}\n2) {item.prompt.split(chr(10))[-1]}"},
        {"prompt": f"{item.prompt} (1 point)"},
        {"prompt": f"{item.prompt} ________"},
    ):
        comparison = compare_exam(exam, mutated_items(exam, index, **update))
        assert comparison.items[index].passed, update


def test_point_and_kind_differences_fail_their_principles():
    exam = gold_exam(_ENGLISH)
    index = question_index(exam, "Vocabulary Matching, Question 1")
    assert _failed(compare_exam(exam, mutated_items(exam, index, points=1)), index) == {"points"}
    as_text = mutated_items(exam, index, kind="free_text", pairs=())
    # The table rows now sit in the open response's text; only type and answer key differ.
    assert _failed(compare_exam(exam, as_text), index) == {"response_kind", "scoring"}


@pytest.mark.parametrize(("stem", "index"), _cases(_multiline_free_text))
def test_a_duplicated_free_text_prompt_passes(stem: str, index: int):
    exam = gold_exam(stem)
    prompt = exam.questions[index].prompt
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=f"{prompt}\n{prompt}"))
    assert comparison.passed


@pytest.mark.parametrize(("stem", "index"), _cases(_multiline_free_text))
def test_reordered_prompt_lines_pass(stem: str, index: int):
    exam = gold_exam(stem)
    lines = exam.questions[index].prompt.split("\n")
    reordered = "\n".join(reversed(lines))
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=reordered))
    assert comparison.passed


@pytest.mark.parametrize(("stem", "index"), _cases(_text_between_gaps))
def test_a_gap_moved_next_to_the_other_gap_passes(stem: str, index: int):
    exam = gold_exam(stem)
    lines = exam.questions[index].prompt.split("\n")
    at = next(i for i, line in enumerate(lines) if line.count("[___]") >= 2)
    parts = lines[at].split("[___]")
    lines[at] = parts[0] + "[___]" * (len(parts) - 1) + "".join(parts[1:])
    comparison = compare_exam(exam, mutated_items(exam, index, prompt="\n".join(lines)))
    assert comparison.passed


@pytest.mark.parametrize(("stem", "index"), _cases(lambda item: len(item.choices) >= 2))
def test_duplicated_or_reordered_choices_pass(stem: str, index: int):
    exam = gold_exam(stem)
    choices = exam.questions[index].choices
    duplicated = compare_exam(exam, mutated_items(exam, index, choices=(*choices, choices[0])))
    assert duplicated.items[index].passed
    swapped = (choices[1], choices[0], *choices[2:])
    assert compare_exam(exam, mutated_items(exam, index, choices=swapped)).items[index].passed


def test_one_removed_gold_word_fails_content():
    exam = gold_exam(_SVENSKA)
    prompt = exam.questions[3].prompt
    word = next(w for w in prompt.split() if w.isalpha() and len(w) > 3)
    removed = re.sub(rf"\b{re.escape(word)}\b", "", prompt, flags=re.IGNORECASE)
    comparison = compare_exam(exam, mutated_items(exam, 3, prompt=removed))
    assert _failed(comparison, 3) == {"content_present"}
    assert comparison.items[3].mismatches[0].expected == (word.casefold(),)


@pytest.mark.parametrize(("stem", "index"), _cases(lambda item: _facit(item) is not None))
def test_the_teachers_facit_shown_for_an_open_question_leaks(stem: str, index: int):
    exam = gold_exam(stem)
    item = exam.questions[index]
    shown = f"{item.prompt}\n{_facit(item)}"
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=shown))
    assert "no_answer_leakage" in _failed(comparison, index)


def test_a_childs_answer_disclosed_in_its_gold_parent_instruction_leaks():
    exam = gold_exam(_DIAGNOSTIC)
    position, parent = next(
        (i, entry) for i, entry in enumerate(exam.items) if isinstance(entry, GoldParent)
    )
    child = parent.children[0]
    index = question_index(exam, child.source_label)
    answer = child.gaps[0].accepted_values[0]
    assert answer == "play"
    assert answer not in parent.instruction.lower()
    assert compare_exam(exam, exam.items).passed

    disclosed = parent.model_copy(update={"instruction": f"{parent.instruction}\n{answer}"})
    assert disclosed.children is parent.children
    items = (*exam.items[:position], disclosed, *exam.items[position + 1 :])
    comparison = compare_exam(exam, items)
    assert not comparison.passed
    assert _failed(comparison, index) == {"no_answer_leakage"}


@pytest.mark.parametrize("stem", [_DIAGNOSTIC, _WORD_BANK])
def test_unchanged_gold_parent_instructions_and_word_banks_do_not_leak(stem: str):
    exam = gold_exam(stem)
    parents = [entry for entry in exam.items if isinstance(entry, GoldParent)]
    assert parents
    if stem == _WORD_BANK:
        assert any(
            value.lower() in parent.instruction.lower()
            for parent in parents
            for child in parent.children
            for gap in child.gaps
            for value in gap.accepted_values
        )
    assert compare_exam(exam, exam.items).passed


def test_a_parent_instruction_moved_onto_every_child_passes():
    exam = gold_exam(_DIAGNOSTIC)
    position, parent = next(
        (i, entry) for i, entry in enumerate(exam.items) if isinstance(entry, GoldParent)
    )
    children = tuple(
        child.model_copy(update={"prompt": f"{parent.instruction}\n{child.prompt}"})
        for child in parent.children
    )
    moved = parent.model_copy(update={"instruction": "Svara.", "children": children})
    items = (*exam.items[:position], moved, *exam.items[position + 1 :])
    assert compare_exam(exam, items).passed


def _adjacent_items(stem: str) -> tuple[GoldExam, int, GoldItem, int, GoldItem]:
    """The exam, its first two adjacent standalone items among the first eight, each with its
    position in the exam's items, and the first item's question index."""
    exam = gold_exam(stem)
    standalone = [i for i, entry in enumerate(exam.items) if isinstance(entry, GoldItem)]
    first, second = next(
        (a, b) for a, b in zip(standalone, standalone[1:], strict=False) if b == a + 1 and a < 8
    )
    one, two = exam.items[first], exam.items[second]
    assert isinstance(one, GoldItem)
    assert isinstance(two, GoldItem)
    return exam, first, one, second, two


def _stems_with_adjacent_items() -> list[str]:
    stems = []
    for stem in STEMS:
        try:
            _adjacent_items(stem)
        except StopIteration:
            continue
        stems.append(stem)
    return stems


def _failing(comparison: ExamComparison) -> dict[int, set[str]]:
    return {i.index: {m.reason for m in i.mismatches} for i in comparison.items if not i.passed}


@pytest.mark.parametrize("stem", _stems_with_adjacent_items())
def test_two_questions_merged_into_one_fail_only_the_merged_pair(stem: str):
    exam, first, one, second, two = _adjacent_items(stem)
    first_index = question_index(exam, one.source_label)
    second_index = question_index(exam, two.source_label)
    merged = one.model_copy(update={"prompt": f"{one.prompt}\n{two.prompt}"})
    items = (*exam.items[:first], merged, *exam.items[second + 1 :])
    comparison = compare_exam(exam, items)
    failing = _failing(comparison)
    assert failing[second_index] == {"missing_item"}
    assert set(failing) <= {first_index, second_index}
    assert len(comparison.items) == len(exam.questions)


@pytest.mark.parametrize("stem", _stems_with_adjacent_items())
def test_one_question_split_into_two_fails_the_split_and_one_extra_item(stem: str):
    exam, first, one, _, _ = _adjacent_items(stem)
    first_index = question_index(exam, one.source_label)
    lines = one.prompt.split("\n")
    head = one.model_copy(update={"prompt": lines[0]})
    tail = one.model_copy(update={"prompt": "\n".join(lines[1:]) or lines[0]})
    items = (*exam.items[:first], head, tail, *exam.items[first + 1 :])
    comparison = compare_exam(exam, items)
    failing = _failing(comparison)
    extra = len(exam.questions)
    assert failing[extra] == {"extra_item"}
    assert set(failing) <= {first_index, extra}
    assert len(comparison.items) == extra + 1


@pytest.mark.parametrize("stem", _stems_with_adjacent_items())
def test_one_dropped_question_is_the_only_missing_item(stem: str):
    exam, first, one, _, _ = _adjacent_items(stem)
    first_index = question_index(exam, one.source_label)
    comparison = compare_exam(exam, (*exam.items[:first], *exam.items[first + 1 :]))
    assert _failing(comparison) == {first_index: {"missing_item"}}


def test_a_question_converted_out_of_order_is_judged_against_its_own_gold():
    exam = gold_exam(_POETRY)
    first, second = exam.items[0], exam.items[1]
    comparison = compare_exam(exam, (second, first, *exam.items[2:]))
    assert comparison.passed


def test_category_grid_pairs_compare_as_sets_not_as_a_sequence():
    exam = gold_exam(AUTHORED_STEM)
    index = question_index(exam, "Fråga 1")
    item = exam.questions[index]
    assert [pair.left for pair in item.pairs].count("vila") == 2
    reversed_pairs = tuple(reversed(item.pairs))
    comparison = compare_exam(exam, mutated_items(exam, index, pairs=reversed_pairs))
    assert comparison.items[index].passed, "pair order must not count"


def test_category_grid_a_tick_moved_to_the_unused_category_fails_scoring():
    exam = gold_exam(AUTHORED_STEM)
    index = question_index(exam, "Fråga 1")
    item = exam.questions[index]
    first, second, *rest = item.pairs
    moved = second.model_copy(update={"right": "Adjektiv"})
    comparison = compare_exam(exam, mutated_items(exam, index, pairs=(first, moved, *rest)))
    assert _failed(comparison, index) == {"scoring"}
