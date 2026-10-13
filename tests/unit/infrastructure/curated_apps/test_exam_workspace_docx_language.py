"""The teacher DOCX export prints its fixed words in the exam's language (D21).

Each corpus exam is converted from its recorded provider rounds and exported. The exam
language is the word gold prints before its question numbers, so no exam is named. Only
lines the writer generates are checked: headings, points lines, the answer-key heading
and answer-key rows. Exam text copied from the source may contain any word.
"""

import io
import re

import pytest
from docx import Document

from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    exam_language_labels,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.scripts.exam_conversion_corpus_support import STEMS, gold_exam, replayed

_SWEDISH = {"Fråga", "Lucka", "Poäng", "poäng", "saknas", "Facit", "Rätt svar", "Par"}
_ENGLISH = {"Question", "Gap", "Points", "missing", "Answer key", "Correct answer", "Pair"}
_KEY_ROW = re.compile(r"^(Rätt svar|Correct answer|Lucka \d+|Gap \d+|Par|Pair): ")


def _gold_label_word(stem: str) -> str:
    label = gold_exam(stem).questions[0].source_label.split(",")[-1]
    match = re.match(r"\s*(\w+)\s+\d", label)
    assert match is not None, label
    return match.group(1)


def _generated_lines(stem: str) -> list[str]:
    """Headings, points lines, the answer-key heading and answer-key rows of the export."""
    document, _ = replayed(stem)
    parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))
    lines: list[str] = []
    for paragraph in parsed.paragraphs:
        style = paragraph.style.name if paragraph.style is not None else ""
        text = paragraph.text
        if (
            style in {"Heading 2", "Heading 3"}
            or text.startswith("Poäng:")
            or text.startswith("Points:")
            or _KEY_ROW.match(text)
        ):
            lines.append(text)
    return lines


def _words_of(text: str) -> set[str]:
    return set(re.findall(r"\w+", text))


@pytest.mark.parametrize("stem", STEMS)
def test_generated_lines_hold_no_fixed_word_of_the_other_language(stem: str) -> None:
    document, _ = replayed(stem)
    labels = exam_language_labels(document)
    assert labels.question == _gold_label_word(stem)
    forbidden = _ENGLISH if labels.language == "sv" else _SWEDISH
    forbidden_words = {word for phrase in forbidden for word in phrase.split()}
    # Lines the exam itself prints are not generated export wording.
    printed = {line for item in document.items for line in item.plain_text_lines()}
    generated = [line for line in _generated_lines(stem) if line not in printed]
    assert generated
    for line in generated:
        foreign = _words_of(line) & forbidden_words
        assert not foreign, f"{stem}: {line!r} holds {sorted(foreign)}"


@pytest.mark.parametrize("stem", STEMS)
def test_every_points_line_and_key_heading_uses_the_exam_language(stem: str) -> None:
    document, _ = replayed(stem)
    labels = exam_language_labels(document)
    parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))
    texts = [paragraph.text for paragraph in parsed.paragraphs]
    for item in document.items:
        points = None if item.points is None else str(int(item.points))
        if item.points is not None and not float(item.points).is_integer():
            continue
        assert labels.points_line(points) in texts
    headings = [
        p.text for p in parsed.paragraphs if p.style is not None and p.style.name == "Heading 2"
    ]
    assert headings in ([], [labels.answer_key])


def test_the_corpus_holds_a_swedish_and_an_english_exam() -> None:
    languages = {exam_language_labels(replayed(stem)[0]).language for stem in STEMS}
    assert {"sv", "en"} <= languages
