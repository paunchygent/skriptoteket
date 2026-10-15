"""One document language per exam, inferred from the document's own text.

The producer must never mix languages per accepted value, so the inference is
checked against Swedish and English bodies, quoted foreign answers and ties.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import (
    infer_exam_document_language,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Eleven skriver att hon inte kan svara på frågan.", "sv"),
        ("The student writes that she cannot answer the question.", "en"),
        ("Han och vi har inte tid.", "sv"),
        ("Ångström", "sv"),
        ("", "sv"),
    ],
)
def test_inference_follows_stopwords(text: str, expected: str) -> None:
    assert infer_exam_document_language(text) == expected


def test_swedish_wins_a_stopword_tie() -> None:
    assert infer_exam_document_language("jag and") == "sv"


def test_quoted_english_answers_do_not_flip_a_swedish_document() -> None:
    document = 'Frågan är vad eleven menar när hon säger "the cat sat on the mat".'
    assert infer_exam_document_language(document) == "sv"


def test_a_quoted_swedish_word_does_not_flip_an_english_document() -> None:
    document = 'The pupil answers "smörgås" and explains why.'
    assert infer_exam_document_language(document) == "en"


def test_inference_is_deterministic() -> None:
    document = "The student writes that she cannot answer the question."
    assert infer_exam_document_language(document) == infer_exam_document_language(document)
