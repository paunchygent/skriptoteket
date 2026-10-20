"""Shared admission builders for the one-item-per-question tests.

The admission, heading and omitted-question tests build the same one-question
state and the same converted reply shape; the grouped check reads the item's
own chunks either way.
"""

from uuid import uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

# Omprov grammatik sve2, live 2026-10-17: one question, numbered sentences under one lead-in.
_QUESTION = (
    ("paragraph", "Uppgift 1.1: Subjekt (4 p)"),
    ("paragraph", "Stryk under subjektet i varje mening."),
    ("paragraph", "1. Hunden skäller på brevbäraren."),
    ("paragraph", "2. I morgon reser min syster till Malmö."),
)
_OTHER = (("paragraph", "Uppgift 1.2: Förklara vad ett predikat är. (2 p)"),)


def _state(
    *questions: tuple[tuple[str, str], ...],
) -> DocxBuildState:
    chunks: list[DocxChunk] = []
    grouped: list[tuple[str, ...]] = []
    for question in questions:
        own: list[str] = []
        for kind, text in question:
            anchor = f"body:{len(chunks) + 1:04d}"
            chunks.append(DocxChunk(anchor, kind, text, text))
            own.append(anchor)
        grouped.append(tuple(own))
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=tuple(chunks),
        questions=tuple(grouped),
    )


def _item(anchors: list[str], text: str, label: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
        "body": [{"segments": [{"kind": "text", "text": text, "accepted_values": []}]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _paragraph_texts(paragraphs: tuple[NativeParagraph, ...]) -> list[str]:
    return [
        segment.text
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _is_source_review(item: NativeExamItem, reason: str) -> bool:
    return (
        item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
        and item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        and item.review.reasons[0] == reason
    )
