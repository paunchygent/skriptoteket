"""Matching items from a recorded conversion, with their answer key removed."""

import json
from pathlib import Path
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
)

_RECORDING = Path(
    "tests/fixtures/exam_conversion/docx_build_v7/"
    "bf26_english_1_unit_test_kap_1_2_med_facit/round1.json"
)


def recorded_matching_items(*, keyed: bool = False) -> tuple[NativeExamItem, ...]:
    """Native matching items of the recording; ``keyed=False`` drops every pair (origin ABSENT)."""

    produced = json.loads(_RECORDING.read_text())["items"]
    items: list[NativeExamItem] = []
    for raw in produced:
        if raw["kind"] != NativeExamItemKind.MATCHING.value:
            continue
        if not keyed:
            raw = {**raw, "match_pairs": []}
        item = native_item(ProducedItem.model_validate(raw))
        sequence = len(items) + 1
        items.append(
            NativeExamItem.model_validate(
                {**dict(item), "item_id": f"item_{sequence:03d}", "sequence": sequence}
            )
        )
    return tuple(items)


def document_of(*items: NativeExamItem, revision: int = 1) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=revision,
        title="Recorded matching items",
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )
