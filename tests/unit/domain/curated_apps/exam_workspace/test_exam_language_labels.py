"""QTI labels follow the exam's own language (TASK-SKRIPT-39-05-03 D18).

Each corpus exam is converted from its recorded provider rounds. The expected label word is
the word gold prints before its question numbers, so the check holds for every exam without
naming one.
"""

import re

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    NUMBERS_ONLY,
    exam_language_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeParagraph,
    NativeTextSegment,
)
from tests.unit.scripts.exam_conversion_corpus_support import STEMS, gold_exam, replayed

_LABEL_WORDS = {"Fråga", "Question", "Lucka", "Gap", "Bild", "Image"}


def _gold_label_word(stem: str) -> str:
    """The word gold prints before a question number, such as "Fråga" in "Fråga 3"."""
    label = gold_exam(stem).questions[0].source_label.split(",")[-1]
    match = re.match(r"\s*(\w+)\s+\d", label)
    assert match is not None, label
    return match.group(1)


@pytest.mark.parametrize("stem", STEMS)
def test_exported_labels_use_the_exam_language(stem: str) -> None:
    document, _ = replayed(stem)
    expected = _gold_label_word(stem)
    labels = exam_language_labels(document)
    assert labels.question == expected
    shown: list[str] = []
    for qti_item in native_exam_to_examnet_qti_items(document):
        for item in (qti_item, *qti_item.children):
            shown.append(item.title)
            shown.extend(gap.label for gap in item.text_entry_gaps)
    words = {word for text in shown for word in re.findall(r"\w+", text)}
    foreign = (_LABEL_WORDS - {labels.question, labels.gap, labels.image}) & words
    assert not foreign, f"{stem} shows labels of another language: {sorted(foreign)}"


@pytest.mark.parametrize("stem", STEMS)
def test_parent_titles_span_their_children_in_the_exam_language(stem: str) -> None:
    document, _ = replayed(stem)
    word = _gold_label_word(stem)
    by_parent = {parent.item_ids[0]: parent for parent in document.parents}
    titles = {item.item_id: item.title for item in native_exam_to_examnet_qti_items(document)}
    for parent in document.parents:
        first = document.item_by_id(parent.item_ids[0]).sequence
        last = document.item_by_id(parent.item_ids[-1]).sequence
        qti_id = parent.parent_id
        assert titles[qti_id] == f"{word} {first}–{last}", (stem, by_parent)


def test_an_untitled_english_item_is_not_labelled_in_swedish() -> None:
    document, _ = replayed("bf26_diagnostic_grammar_test_ht26_med_facit")
    untitled = document.model_copy(
        update={"items": tuple(item.model_copy(update={"title": None}) for item in document.items)}
    )
    titles = [item.title for item in native_exam_to_examnet_qti_items(untitled)]
    assert all(not title.startswith("Fråga") for title in titles)
    assert "Question 19" in titles


def _numbers_only(item: NativeExamItem) -> NativeExamItem:
    digits = NativeParagraph(segments=(NativeTextSegment(text="12 + 30 = 42"),))
    return item.model_copy(update={"title": None, "body": (digits,), "choices": ()})


def test_an_exam_without_words_of_a_known_language_gets_bare_numbers() -> None:
    document, _ = replayed("svenska_2_kursavslutande_prov_med_facit")
    free_text = next(item for item in document.items if item.kind.value == "free_text")
    numbers = document.model_copy(
        update={
            "title": "2026",
            "instructions": (),
            "parents": (),
            "items": (_numbers_only(free_text).model_copy(update={"sequence": 1}),),
        }
    )
    assert exam_language_labels(numbers) == NUMBERS_ONLY
    assert [item.title for item in native_exam_to_examnet_qti_items(numbers)] == ["1"]
