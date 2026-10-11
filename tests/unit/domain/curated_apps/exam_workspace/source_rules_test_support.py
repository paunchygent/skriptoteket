"""Real corpus chunks and recorded model items for the source-rule tests."""

import json
from pathlib import Path

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import item_rule_violation
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

FIXTURES = Path("tests/fixtures/exam_conversion")


def chunks_by_anchor(docx: str) -> dict[str, DocxChunk]:
    chunks = PythonDocxExamChunker().chunk(
        content=(FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    return {chunk.anchor: chunk for chunk in chunks}


def recorded_produced_items(recording: str) -> list[ProducedItem]:
    content = json.loads((FIXTURES / recording).read_text())
    return [ProducedItem.model_validate(raw) for raw in content["items"]]


def item_violations(recording: str, docx: str) -> dict[tuple[str, ...], str | None]:
    chunks = chunks_by_anchor(docx)
    return {
        item.source_anchors: item_rule_violation(item, [chunks[a] for a in item.source_anchors])
        for item in recorded_produced_items(recording)
    }
