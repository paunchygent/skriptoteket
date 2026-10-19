"""Fail-first DOCX tests for inline "(N p)" points (TASK-SKRIPT-40-04-15 U1).

The DOCX student copy renders the shared print document, so each question's points print
as "(N p)" at the end of its last question-text paragraph, plain (not bold), with no
separate "Poäng:" paragraph. These tests fail on the current code, which still renders
the bold "Poäng: N poäng" paragraph from the print document.
"""

import io

from docx import Document
from docx.text.paragraph import Paragraph

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_paragraph,
    make_review,
    plain_body,
)


def _docx_paragraphs() -> list[Paragraph]:
    stem = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(make_paragraph("Vilket problem prövas?"),),
        points=1,
        writing_lines=3,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )
    choice = NativeExamItem(
        item_id="item_002",
        sequence=2,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(make_paragraph("Vilket ord är verb?"),),
        points=2,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("hus")),
            NativeChoice(choice_id="choice_002", body=plain_body("springer")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_002",),
        ),
        review=make_review(),
    )
    content = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(
        make_document(stem, choice)
    )
    return list(Document(io.BytesIO(content)).paragraphs)


def test_stem_paragraph_ends_with_inline_points() -> None:
    texts = [paragraph.text for paragraph in _docx_paragraphs()]

    assert "Vilket problem prövas? (1 p)" in texts
    assert "Vilket ord är verb? (2 p)" in texts


def test_no_paragraph_starts_with_a_points_line() -> None:
    for paragraph in _docx_paragraphs():
        assert not paragraph.text.startswith("Poäng:")


def test_inline_points_run_is_not_bold() -> None:
    matches = [
        paragraph
        for paragraph in _docx_paragraphs()
        if paragraph.text == "Vilket problem prövas? (1 p)"
    ]

    assert matches, "stem paragraph with inline points is missing"
    point_runs = [run for run in matches[0].runs if "(1 p)" in (run.text or "")]

    assert point_runs
    assert all(run.font.bold in (False, None) for run in point_runs)
