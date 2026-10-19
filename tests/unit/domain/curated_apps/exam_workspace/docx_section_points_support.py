"""Shared builders for DOCX section-points scorer tests."""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import review_chunk_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import printed_points_plan
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
    ScoredItems,
    apply_printed_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent


def _exam(*lines: str) -> tuple[tuple[DocxChunk, ...], tuple[tuple[str, ...], ...]]:
    """Chunks from source lines: "# " marks a heading and "Q " a question's opening line."""
    chunks: list[DocxChunk] = []
    questions: list[tuple[str, ...]] = []
    for number, line in enumerate(lines):
        anchor = f"body:{number:04d}"
        kind = "heading" if line.startswith("# ") else "paragraph"
        text = line.removeprefix("# ").removeprefix("Q ")
        chunks.append(DocxChunk(anchor, kind, text, text))
        if line.startswith("Q "):
            questions.append((anchor,))
    return tuple(chunks), tuple(questions)


def _items(
    chunks: tuple[DocxChunk, ...],
    questions: tuple[tuple[str, ...], ...],
    points: tuple[int | float | None, ...],
) -> tuple[NativeExamItem, ...]:
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    return tuple(
        review_chunk_item(by_anchor[own[0]], "test").model_copy(
            update={"item_id": f"item_{n:03d}", "sequence": n, "points": p}
        )
        for n, (own, p) in enumerate(zip(questions, points, strict=True), 1)
    )


def _score(
    chunks: tuple[DocxChunk, ...],
    questions: tuple[tuple[str, ...], ...],
    items: tuple[NativeExamItem, ...],
    parents: tuple[NativeExamParent, ...] = (),
) -> ScoredItems:
    return apply_printed_points(
        items,
        parents,
        printed_points_plan(chunks, questions),
        {chunk.anchor: chunk for chunk in chunks},
    )


def _points(scored: ScoredItems) -> list[int | float | None]:
    return [item.points for item in scored.items]


def _marked(scored: ScoredItems) -> list[bool]:
    return [item.points_estimated for item in scored.items]


def _source_points(scored: ScoredItems) -> list[int | float | None]:
    return [item.source_points for item in scored.items]


def _parent(parent_id: str, *item_ids: str) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        place=int(item_ids[0].removeprefix("item_")) - 1,
        instruction=(
            NativeParagraph(
                segments=(NativeTextSegment(kind="text", text="Del", marks=()),), heading_level=None
            ),
        ),
        item_ids=item_ids,
    )


_DEL_1 = ("# Del 1: litteraturhistoria, 15 poäng", *(f"Q {n}. Fråga {n}" for n in range(1, 16)))
