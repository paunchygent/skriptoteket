"""The eight gold exams and their live replays, for the comparator tests."""

from __future__ import annotations

import asyncio
from functools import cache
from pathlib import Path

from scripts.exam_conversion_eval.gold import GoldExam, GoldItem, GoldParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    build_replay,
)

CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
GOLD = CORPUS / "gold"
STEMS = tuple(sorted(path.stem for path in GOLD.glob("*.json")))
# The agent-authored grid exam has no live recording; tests that replay use the recorded set.
AUTHORED_STEM = "svenska_2_kategorisera_ordklasser_med_facit"
RECORDED_STEMS = tuple(sorted(path.name for path in RECORDINGS.iterdir() if path.is_dir()))


def gold_exam(stem: str) -> GoldExam:
    return GoldExam.model_validate_json((GOLD / f"{stem}.json").read_text())


def mutated_items(
    exam: GoldExam, index: int, **update: object
) -> tuple[GoldItem | GoldParent, ...]:
    """The exam's items with the question at the flat index changed, parents kept."""
    position = 0
    items: list[GoldItem | GoldParent] = []
    for entry in exam.items:
        if isinstance(entry, GoldParent):
            children: list[GoldItem] = []
            for child in entry.children:
                children.append(child.model_copy(update=update) if position == index else child)
                position += 1
            items.append(entry.model_copy(update={"children": tuple(children)}))
        else:
            items.append(entry.model_copy(update=update) if position == index else entry)
            position += 1
    return tuple(items)


def question_index(exam: GoldExam, label: str) -> int:
    return next(i for i, item in enumerate(exam.questions) if item.source_label == label)


@cache
def replayed(
    stem: str, recordings: Path = RECORDINGS
) -> tuple[NativeExamDocument, tuple[str, ...]]:
    """The exam converted from its live recorded replies, with the source chunk texts.

    The conversion is the production pipeline over the fresh recordings; the result is a
    real, non-gold document that the comparator tests then mutate deliberately. This helper
    runs the pipeline to completion with ``asyncio.run``, so it is for synchronous tests only.
    """
    replay = build_replay(stem, root=recordings)
    job = replay.job()
    outcome = asyncio.run(replay.pipeline.convert(job=job))
    return outcome.result.document, tuple(chunk.text for chunk in job.chunks)


def with_item(document: NativeExamDocument, index: int, item: NativeExamItem) -> NativeExamDocument:
    items = list(document.items)
    items[index] = item
    return document.model_copy(update={"items": tuple(items)})
