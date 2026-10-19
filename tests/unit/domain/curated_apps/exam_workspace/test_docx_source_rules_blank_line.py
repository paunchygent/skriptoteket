"""Blank answer lines are the response space the item's gap or answer field takes."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import blank_line

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "text",
    [
        "________________",
        "  ____  ____ ",
        "[ ]",
        "3. __________",
    ],
)
def test_a_line_of_blank_runs_only_is_a_blank_answer_line(text: str) -> None:
    assert blank_line(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Answer: ____",
        "We live in ____ (ett eget hus).",
        "_",
        "Two words are extra.",
    ],
)
def test_a_line_with_question_text_or_no_blank_run_is_not_a_blank_answer_line(text: str) -> None:
    assert not blank_line(text)
