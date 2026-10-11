"""The eight gold exams and their recorded conversions, for the comparator tests."""

import json
from functools import cache
from pathlib import Path
from uuid import uuid4

from scripts.exam_conversion_eval.gold import GoldExam, GoldItem, GoldParent
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
GOLD = CORPUS / "gold"
RECORDINGS = Path("tests/fixtures/exam_conversion/docx_build_v7")
STEMS = tuple(sorted(path.stem for path in GOLD.glob("*.json")))


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
    """The exam converted from its recorded provider rounds, with the source chunk texts."""
    chunks = PythonDocxExamChunker().chunk(content=(CORPUS / f"{stem}.docx").read_bytes())
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{stem}.docx",
        source_sha256="0" * 64,
        chunks=chunks,
    )
    for recorded in sorted((recordings / stem).glob("round*.json")):
        admit_batch(json.loads(recorded.read_text()), state)
    return state.result().document, tuple(chunk.text for chunk in chunks)


def with_item(document: NativeExamDocument, index: int, item: NativeExamItem) -> NativeExamDocument:
    items = list(document.items)
    items[index] = item
    return document.model_copy(update={"items": tuple(items)})
