"""F1: printed question points are fixed before a part shares its remaining total.

The production build result runs over a part that prints 10 points: q1 prints 2 and the
reply says 8; q2 prints none. Whatever the reply says, q2 takes the 8 that remain.
"""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import review_chunk_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
)

pytestmark = pytest.mark.unit


def _chunk(anchor: str, kind: str, text: str, level: int | None = None) -> DocxChunk:
    paragraphs = (DocxSourceParagraph(0, text, level),) if level is not None else ()
    return DocxChunk(anchor, kind, text, text, paragraphs=paragraphs)


@pytest.mark.parametrize(
    ("q1_reply", "line_tag"),
    [(2, None), (8, None), (8, "header"), (1, None)],
)
def test_the_part_shares_what_remains_after_the_printed_question_points(
    q1_reply: int, line_tag: str | None
) -> None:
    chunks = (
        _chunk("body:0001", "heading", "Del 1: 10 poäng"),
        _chunk("body:0002", "paragraph", "1. Förklara tempus."),
        _chunk("body:0003", "paragraph", "Poäng: 2 poäng"),
        _chunk("body:0004", "paragraph", "2. Förklara modus."),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="del.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0002", "body:0003"), ("body:0004",)),
        header_anchors=frozenset({"body:0003"}) if line_tag == "header" else frozenset(),
    )
    for anchor, points in (("body:0002", q1_reply), ("body:0004", None)):
        item = review_chunk_item(chunks[int(anchor[-1]) - 1], "test")
        state.accepted.append((item.model_copy(update={"points": points}), (anchor,)))
    state.claimed.update(chunk.anchor for chunk in chunks)

    document = state.result().document

    assert [item.points for item in document.items] == [2, 8]
    assert [item.points_estimated for item in document.items] == [False, False]


@pytest.mark.parametrize("next_rank", [1, 2, 3, None])
def test_a_section_parent_ends_at_the_next_part_heading_whatever_its_rank(
    next_rank: int | None,
) -> None:
    """Review-5: "Del 2" opens a part, so Del 1's parent never absorbs q3 by heading rank."""
    chunks = (
        _chunk("body:0000", "paragraph", "Grammatikprov"),
        _chunk("body:0001", "heading", "Del 1: 2 poäng", 1),
        _chunk("body:0002", "paragraph", "1. Förklara tempus."),
        _chunk("body:0003", "paragraph", "2. Förklara modus."),
        _chunk("body:0004", "heading", "Del 2: 7 poäng", next_rank),
        _chunk("body:0005", "paragraph", "3. Förklara aspekt."),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="del.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0002",), ("body:0003",), ("body:0005",)),
    )
    for chunk in (chunks[2], chunks[3], chunks[5]):
        state.accepted.append((review_chunk_item(chunk, "test"), (chunk.anchor,)))
    state.claimed.update(chunk.anchor for chunk in chunks)

    document = state.result().document

    assert [(p.item_ids, p.printed_total) for p in document.parents] == [
        (("item_001", "item_002"), 2)
    ]
    assert [item.points for item in document.items] == [1, 1, 7]
