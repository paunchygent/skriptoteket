"""A question's lead-in lines never land in another question's body (TASK-SKRIPT-39-04-12, C1).

Synthetic placement: each question prints a heading line, an instruction line and then
numbered lines, and the reply builds one item per question. Lines a question prints before
its first numbered line belong to that question alone.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    Placed,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)


def _chunk(anchor: str, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind=kind, text=text, marked_text=text)


def _item(sequence: int, lines: tuple[str, ...]) -> NativeExamItem:
    return NativeExamItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=tuple(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=t, marks=()),))
            for t in lines
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
    )


@pytest.mark.parametrize("heading_kind", ["paragraph", "heading"])
def test_lead_in_of_one_question_never_lands_in_the_next_question(heading_kind: str) -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", heading_kind, "Uppgift 1.1: Verb (4 p)"),
        _chunk("body:0003", "paragraph", "Skriv verbets tempus."),
        _chunk("body:0004", "paragraph", "1. springer"),
        _chunk("body:0005", "paragraph", "2. sprang"),
        _chunk("body:0006", heading_kind, "Uppgift 1.2: Substantiv (4 p)"),
        _chunk("body:0007", "paragraph", "Skriv substantivets numerus."),
        _chunk("body:0008", "paragraph", "1. hund"),
        _chunk("body:0009", "paragraph", "2. hundar"),
    )
    ordered: list[Placed] = [
        (
            1,
            ("body:0002", "body:0003", "body:0004", "body:0005"),
            _item(1, ("1. springer", "2. sprang")),
        ),
        (
            5,
            ("body:0006", "body:0007", "body:0008", "body:0009"),
            _item(2, ("1. hund", "2. hundar")),
        ),
    ]

    placed = place_section_instructions(chunks, ordered, (), {}, frozenset({"body:0001"}))

    second = placed.items[1].plain_text_lines()
    assert not any("Uppgift 1.1" in line or "verbets tempus" in line for line in second)
    assert placed.parents == ()
    assert "1. hund" in second
