"""Real corpus chunks and fresh recorded model items for the source-transform tests."""

from pathlib import Path

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    recorded_converted_items,
)

FIXTURES = Path("tests/fixtures/exam_conversion")


def chunks_by_anchor(docx: str) -> dict[str, DocxChunk]:
    chunks = PythonDocxExamChunker().chunk(
        content=(FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    return {chunk.anchor: chunk for chunk in chunks}


def recorded_produced_items(exam: str) -> list[ProducedItem]:
    """Every converted item the exam's fresh recordings returned, in source order."""
    return list(recorded_converted_items(exam))
