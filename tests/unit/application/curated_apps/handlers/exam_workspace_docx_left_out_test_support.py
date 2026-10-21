"""Shared admission builders for the left-out own-chunk tests.

Both the unlisted left-out tests and the listed-chunk tests build the same one-question
state and the same converted reply shape; the grouped check reads the item's own chunks
either way.
"""

from uuid import uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)

_STEM = "1. Beskriv kort hur en intervju planeras."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _state(*texts: str, grouped_keys: frozenset[str] = frozenset()) -> DocxBuildState:
    chunks = tuple(_chunk(f"body:{n:04d}", text) for n, text in enumerate(texts, start=1))
    return DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(c.anchor for c in chunks),),
        grouped_keys=grouped_keys,
    )


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _stem_texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _item(anchors: list[str], **fields: JsonValue) -> dict[str, JsonValue]:
    item: dict[str, JsonValue] = {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": "1",
        "body": [{"segments": [_text(_STEM[3:])]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }
    item.update(fields)
    return item
