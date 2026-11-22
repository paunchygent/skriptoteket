"""The labeling report reads the saved facit output the writer produces.

``facit_attachment`` saves ``{"keys": [...], "answers": {...}}``; the report
scores only the ``answers`` map. The test saves that envelope through the real
writer and reads it back through ``report.evaluate_exam_run`` against one real
corpus exam; no provider is called.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import JsonValue

from scripts.labeling_feasibility import __main__ as feasibility_main
from scripts.labeling_feasibility import methods, report
from scripts.labeling_feasibility.api import CallRecord, OpenAIClient
from scripts.labeling_feasibility.method_models import Grouping, Question
from scripts.labeling_feasibility.requests import MethodResult

pytestmark = pytest.mark.unit


class _ChoosingClient(OpenAIClient):
    """Answers every Decisions question with the choice ``q1`` and sends nothing."""

    def __init__(self) -> None:
        pass

    async def decisions(
        self,
        *,
        label: str,
        input_value: str | Sequence[Mapping[str, JsonValue]],
        questions: Sequence[Mapping[str, JsonValue]],
    ) -> CallRecord:
        answers: list[JsonValue] = [
            {"name": question["name"], "type": "choice", "choice": "q1"} for question in questions
        ]
        return CallRecord("decisions", label, 200, 0.1, {}, {"answers": answers})


@pytest.mark.asyncio
async def test_report_scores_the_facit_answers_of_the_saved_envelope(tmp_path: Path) -> None:
    docx = sorted(report.CORPUS.glob("*.docx"))[0]
    gold, chunks, reference = report.load_reference(docx)
    item = reference.items[0]
    grouping = Grouping(
        method="a",
        questions=[Question(id="q1", anchors=list(item.content), key_anchors=list(item.key))],
        contexts=[],
        title=[],
        other=[],
    )
    facit = await methods.facit_attachment(_ChoosingClient(), "facit", grouping, chunks)
    exam_dir = tmp_path / docx.stem
    feasibility_main._save(
        exam_dir / "grouping_a.json", MethodResult([], grouping.to_json()), grouping.to_json()
    )
    feasibility_main._save(exam_dir / "facit_a.json", facit, facit.output)

    saved = json.loads((exam_dir / "facit_a.json").read_text())
    assert sorted(saved["output"]) == ["answers", "keys"]
    assert saved["output"]["keys"] == list(item.key)

    result = report.evaluate_exam_run(exam_dir, gold, chunks, reference)

    scores = result["facit_a"]
    assert scores["asked"] == len(item.key)
    assert scores["decisions_correct"] == len(item.key)
