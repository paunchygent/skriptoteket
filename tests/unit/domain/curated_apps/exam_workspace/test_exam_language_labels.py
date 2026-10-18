"""QTI labels are Swedish for every exam (user decision of 2026-10-18).

Each corpus exam is converted from its recorded provider rounds, whatever language it is
written in; the words the export adds are always the one Swedish label set.
"""

import re

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from tests.unit.scripts.exam_conversion_corpus_support import RECORDED_STEMS, replayed

_ENGLISH_LABEL_WORDS = {"Question", "Gap", "Image"}


@pytest.mark.parametrize("stem", RECORDED_STEMS)
def test_exported_labels_are_swedish(stem: str) -> None:
    document, _ = replayed(stem)
    shown: list[str] = []
    for qti_item in native_exam_to_examnet_qti_items(document):
        # A parent title spans the children's printed labels, which are the source's own words.
        leaves = qti_item.children or (qti_item,)
        for item in leaves:
            shown.append(item.title)
            shown.extend(gap.label for gap in item.text_entry_gaps)
    words = {word for text in shown for word in re.findall(r"\w+", text)}
    foreign = _ENGLISH_LABEL_WORDS & words
    assert not foreign, f"{stem} shows English labels: {sorted(foreign)}"


@pytest.mark.parametrize("stem", RECORDED_STEMS)
def test_parent_titles_span_their_children_in_swedish(stem: str) -> None:
    document, _ = replayed(stem)
    labels = SWEDISH_EXAM_LABELS
    titles = {item.item_id: item.title for item in native_exam_to_examnet_qti_items(document)}
    for parent in document.parents:
        children = [document.item_by_id(item_id) for item_id in parent.item_ids]
        first, last = children[0], children[-1]
        # Parents span printed labels (including letters/restarted numbering),
        # falling back to running numbers only if a child has no printed label.
        expected = (
            labels.printed_span(first.printed_label or "", last.printed_label or "")
            if all(child.printed_label for child in children)
            else labels.question_label(first.sequence, last.sequence)
        )
        assert titles[parent.parent_id] == expected, (stem, parent.parent_id)


def test_an_english_item_is_labelled_in_swedish() -> None:
    document, _ = replayed("bf26_diagnostic_grammar_test_ht26_med_facit")
    titles = [item.title for item in native_exam_to_examnet_qti_items(document)]
    assert "Fråga 19" in titles
    assert not any(title.startswith("Question") for title in titles)
