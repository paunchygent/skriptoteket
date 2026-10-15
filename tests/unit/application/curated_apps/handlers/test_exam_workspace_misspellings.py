"""Teacher keying uses exactly one document-wide producer language."""

from typing import Literal

import pytest

from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
)
from skriptoteket.application.curated_apps.handlers import exam_workspace_misspellings as app

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Vad är detta och hur fungerar det?", "sv"),
        ("What is this and how does it work?", "en"),
        ("", "sv"),
    ],
)
def test_passes_document_language_and_complete_gold_set(
    monkeypatch: pytest.MonkeyPatch, text: str, language: Literal["sv", "en"]
) -> None:
    calls: list[tuple[tuple[str, ...], str, tuple[str, ...]]] = []

    def producer(
        accepted_values: tuple[str, ...],
        *,
        language: Literal["sv", "en"],
        other_gold_answers: tuple[str, ...],
    ) -> tuple[str, ...]:
        calls.append((accepted_values, language, other_gold_answers))
        return ("Stockholn",)

    monkeypatch.setattr(app, "produce_answer_misspellings", producer)
    request = ExamWorkspaceMisspellingsRequest(
        accepted_values=("Stockholm",),
        other_gold_answers=("Stockholm", "Oslo"),
        document_text=text,
    )
    result = app.GenerateExamWorkspaceMisspellingsHandler().handle(request=request)
    assert result.automatic_values == ("Stockholn",)
    assert calls == [(request.accepted_values, language, request.other_gold_answers)]
