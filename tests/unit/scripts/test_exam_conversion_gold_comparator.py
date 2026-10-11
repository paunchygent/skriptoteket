"""The principle comparator judged on real gold questions and conversions breaking a principle."""

import pytest

from scripts.exam_conversion_eval.compare import (
    PRINCIPLES,
    ExamComparison,
    compare_exam,
)
from scripts.exam_conversion_eval.gold import GoldExam, GoldGap, GoldItem, GoldParent
from tests.unit.scripts.exam_conversion_corpus_support import (
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


def test_answer_written_into_the_prompt_leaks_and_loses_the_slot():
    exam = gold_exam(_ENGLISH)
    index = question_index(exam, "Grammar and Corrections, Question 7")
    item = exam.questions[index]
    answer = item.gaps[0].accepted_values[0]
    filled = item.prompt.replace("[___]", answer)
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=filled, gaps=()))
    assert _failed(comparison, index) == {
        "no_answer_leakage",
        "response_slots",
        "scoring",
        "content_present",
    }


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


def test_text_of_the_neighbouring_question_fails_segmentation():
    """A live round copied question 7's wording into question 8."""
    exam = gold_exam(_POETRY)
    seventh = question_index(exam, "Part 1, Question 7")
    prompt = exam.questions[seventh].prompt
    comparison = compare_exam(exam, mutated_items(exam, seventh + 1, prompt=prompt))
    assert _failed(comparison, seventh + 1) == {"segmentation", "content_present"}
    assert comparison.items[seventh].passed


def test_a_single_foreign_word_of_another_questions_phrase_fails_segmentation():
    exam = gold_exam(_POETRY)
    seventh = question_index(exam, "Part 1, Question 7")
    own = exam.questions[seventh + 1].prompt
    foreign = exam.questions[seventh].prompt.split("\n")[0]
    comparison = compare_exam(exam, mutated_items(exam, seventh + 1, prompt=f"{own}\n{foreign}"))
    assert "segmentation" in _failed(comparison, seventh + 1)


def test_option_letters_question_numbers_points_and_blanks_fail_labels():
    exam = gold_exam(_POETRY)
    index = question_index(exam, "Part 1, Question 7")
    item = exam.questions[index]
    lettered = tuple(f"{chr(65 + i)}. {choice}" for i, choice in enumerate(item.choices))
    for update in (
        {"choices": lettered, "correct_choices": (lettered[item.choices.index("speaker")],)},
        {"prompt": f"7. {item.prompt}"},
        {"prompt": f"{item.prompt}\n2) {item.prompt.split(chr(10))[-1]}"},
        {"prompt": f"{item.prompt} (1 point)"},
        {"prompt": f"{item.prompt} ________"},
    ):
        comparison = compare_exam(exam, mutated_items(exam, index, **update))
        assert "no_platform_labels" in _failed(comparison, index), update


def test_point_and_kind_differences_fail_their_principles():
    exam = gold_exam(_ENGLISH)
    index = question_index(exam, "Vocabulary Matching, Question 1")
    assert _failed(compare_exam(exam, mutated_items(exam, index, points=1)), index) == {"points"}
    as_text = mutated_items(exam, index, kind="free_text", pairs=())
    # The table rows now sit in the open response's text as numbered lines.
    assert _failed(compare_exam(exam, as_text), index) == {
        "response_kind",
        "response_slots",
        "scoring",
        "no_platform_labels",
    }


@pytest.mark.parametrize(("stem", "index"), _cases(_multiline_free_text))
def test_a_duplicated_free_text_prompt_fails_segmentation(stem: str, index: int):
    exam = gold_exam(stem)
    prompt = exam.questions[index].prompt
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=f"{prompt}\n{prompt}"))
    assert _failed(comparison, index) == {"segmentation"}
    assert [i.index for i in comparison.items if not i.passed] == [index]


@pytest.mark.parametrize(("stem", "index"), _cases(_multiline_free_text))
def test_reversed_subparts_fail_segmentation(stem: str, index: int):
    exam = gold_exam(stem)
    lines = exam.questions[index].prompt.split("\n")
    reversed_prompt = "\n".join(reversed(lines))
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=reversed_prompt))
    assert _failed(comparison, index) == {"segmentation"}


@pytest.mark.parametrize(("stem", "index"), _cases(_text_between_gaps))
def test_a_gap_moved_next_to_the_other_gap_fails_response_slots_only(stem: str, index: int):
    exam = gold_exam(stem)
    lines = exam.questions[index].prompt.split("\n")
    at = next(i for i, line in enumerate(lines) if line.count("[___]") >= 2)
    parts = lines[at].split("[___]")
    lines[at] = parts[0] + "[___]" * (len(parts) - 1) + "".join(parts[1:])
    comparison = compare_exam(exam, mutated_items(exam, index, prompt="\n".join(lines)))
    assert _failed(comparison, index) == {"response_slots"}


@pytest.mark.parametrize(("stem", "index"), _cases(lambda item: len(item.choices) >= 2))
def test_a_duplicated_or_reordered_choice_fails_response_slots(stem: str, index: int):
    exam = gold_exam(stem)
    choices = exam.questions[index].choices
    duplicated = compare_exam(exam, mutated_items(exam, index, choices=(*choices, choices[0])))
    assert "response_slots" in _failed(duplicated, index)
    swapped = (choices[1], choices[0], *choices[2:])
    reordered = compare_exam(exam, mutated_items(exam, index, choices=swapped))
    assert _failed(reordered, index) == {"response_slots"}


@pytest.mark.parametrize(("stem", "index"), _cases(lambda item: _facit(item) is not None))
def test_the_teachers_facit_shown_for_an_open_question_leaks(stem: str, index: int):
    exam = gold_exam(stem)
    item = exam.questions[index]
    shown = f"{item.prompt}\n{_facit(item)}"
    comparison = compare_exam(exam, mutated_items(exam, index, prompt=shown))
    assert "no_answer_leakage" in _failed(comparison, index)


def test_a_question_number_on_a_later_line_fails_labels():
    exam = gold_exam(_SVENSKA)
    item = exam.questions[0]
    first, *rest = item.prompt.split("\n")
    numbered = "\n".join([first, f"1. {rest[0]}", *rest[1:]])
    comparison = compare_exam(exam, mutated_items(exam, 0, prompt=numbered))
    assert "no_platform_labels" in _failed(comparison, 0)


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
