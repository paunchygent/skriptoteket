"""R4: a rewritten multi-anchor instruction keeps the whole identified source body.

Purpose:
    A converted question's instruction may name several source chunks and rewrite
    their wording. No single source paragraph can then be selected, and the
    per-paragraph projection refuses to pick one. The contracted answer is the
    complete body of every identified source chunk, in the document's source
    order, with the source marks and paragraph levels intact. Source pictures
    keep their existing fail-closed rule.

Relationships:
    - Exercises `domain.docx_ai_build.assemble_build_result` and
      `domain.source_formatted_instructions.instruction_paragraphs`.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    aligned_native_item,
    assemble_build_result,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatted_instructions import (
    instruction_paragraphs,
)

pytestmark = pytest.mark.unit


def _as_text(segment: NativeSegment) -> NativeTextSegment:
    assert isinstance(segment, NativeTextSegment)
    return segment


_BOLD: tuple[str, ...] = ("bold",)
_ITALIC: tuple[str, ...] = ("italic",)
_UNDERLINE: tuple[str, ...] = ("underline",)


def _paragraph_chunk(
    anchor: str,
    text: str,
    *,
    marks: tuple[str, ...] = (),
    heading_level: int | None = None,
) -> DocxChunk:
    runs = (DocxSourceRun(0, text, marks),) if marks else ()
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=runs,
        paragraphs=(DocxSourceParagraph(0, text, heading_level),),
    )


def _instruction_chunks() -> tuple[DocxChunk, DocxChunk, DocxChunk]:
    return (
        _paragraph_chunk("body:0001", "Do not use calculators.", marks=_BOLD),
        _paragraph_chunk("body:0002", "Read every instruction.", marks=_ITALIC),
        _paragraph_chunk("body:0003", "Exam rules", marks=_UNDERLINE, heading_level=2),
    )


def _rewritten_instruction(anchors: tuple[str, ...]) -> ProducedMetadata:
    return ProducedMetadata(text="Follow these guidelines.", source_anchors=anchors)


def _converted(anchor: str, text: str) -> AlignedItem:
    return aligned_native_item(
        ProducedItem(
            source_anchors=(anchor,),
            outcome="converted",
            kind=NativeExamItemKind.FREE_TEXT,
            review_reason=None,
            body=(
                ProducedParagraph(
                    segments=(ProducedSegment(kind="text", text=text, accepted_values=()),)
                ),
            ),
            key_source=None,
            facit_text=None,
            points=1,
            choices=(),
        ),
        language="en",
    )


def _rendered(
    paragraphs: tuple[NativeParagraph, ...],
) -> list[list[tuple[str, tuple[str, ...]]]]:
    return [
        [(_as_text(segment).text, _as_text(segment).marks) for segment in paragraph.segments]
        for paragraph in paragraphs
    ]


def test_a_rewritten_instruction_without_a_selectable_paragraph_keeps_its_source_body() -> None:
    bold, italic, heading = _instruction_chunks()
    instruction = _rewritten_instruction((bold.anchor, italic.anchor, heading.anchor))

    paragraphs = instruction_paragraphs(
        instruction, {chunk.anchor: chunk for chunk in (bold, italic, heading)}
    )

    assert [paragraph.heading_level for paragraph in paragraphs] == [None, None, 2]
    assert _rendered(paragraphs) == [
        [("Do not use calculators.", _BOLD)],
        [("Read every instruction.", _ITALIC)],
        [("Exam rules", _UNDERLINE)],
    ]
    assert body_plain_text(paragraphs) == (
        "Do not use calculators.\nRead every instruction.\nExam rules"
    )


def test_full_assembly_keeps_a_rewritten_multi_anchor_instruction_source_backed() -> None:
    question = _paragraph_chunk("body:0000", "Answer this question.")
    bold, italic, heading = _instruction_chunks()
    instruction = _rewritten_instruction((bold.anchor, italic.anchor, heading.anchor))

    result = assemble_build_result(
        document_id=uuid4(),
        filename="instructions.docx",
        source_sha256="a" * 64,
        chunks=(question, bold, italic, heading),
        accepted=((_converted("body:0000", "Answer this question."), ("body:0000",)),),
        review_reasons={},
        instructions=(instruction,),
    )

    paragraphs = result.document.instructions
    assert [paragraph.heading_level for paragraph in paragraphs] == [None, None, 2]
    assert _rendered(paragraphs) == [
        [("Do not use calculators.", _BOLD)],
        [("Read every instruction.", _ITALIC)],
        [("Exam rules", _UNDERLINE)],
    ]
    assert body_plain_text(paragraphs) == (
        "Do not use calculators.\nRead every instruction.\nExam rules"
    )


def test_full_assembly_reconstructs_a_reversed_anchor_list_in_source_order() -> None:
    question = _paragraph_chunk("body:0000", "Answer this question.")
    bold, italic, heading = _instruction_chunks()
    instruction = _rewritten_instruction((heading.anchor, italic.anchor, bold.anchor))

    result = assemble_build_result(
        document_id=uuid4(),
        filename="instructions.docx",
        source_sha256="a" * 64,
        chunks=(question, bold, italic, heading),
        accepted=((_converted("body:0000", "Answer this question."), ("body:0000",)),),
        review_reasons={},
        instructions=(instruction,),
    )

    paragraphs = result.document.instructions
    assert [paragraph.heading_level for paragraph in paragraphs] == [None, None, 2]
    assert _rendered(paragraphs) == [
        [("Do not use calculators.", _BOLD)],
        [("Read every instruction.", _ITALIC)],
        [("Exam rules", _UNDERLINE)],
    ]


def test_a_shortened_instruction_keeps_its_source_body_even_with_answer_key_wording() -> None:
    key_line = _paragraph_chunk("body:0001", "Answer key: keep this line.")
    marked = DocxChunk(
        "body:0002",
        "paragraph",
        "Keep this. Read that.",
        "Keep this. Read that.",
        runs=(
            DocxSourceRun(0, "Keep this.", _BOLD),
            DocxSourceRun(10, " Read that.", _ITALIC),
        ),
        paragraphs=(DocxSourceParagraph(0, "Keep this. Read that.", None),),
    )
    instruction = ProducedMetadata(
        text="Keep this.", source_anchors=(key_line.anchor, marked.anchor)
    )

    paragraphs = instruction_paragraphs(
        instruction, {chunk.anchor: chunk for chunk in (key_line, marked)}
    )

    assert [paragraph.heading_level for paragraph in paragraphs] == [None, None]
    assert _rendered(paragraphs) == [
        [("Answer key: keep this line.", ())],
        [("Keep this.", _BOLD), (" Read that.", _ITALIC)],
    ]
    assert body_plain_text(paragraphs) == ("Answer key: keep this line.\nKeep this. Read that.")


def test_a_rewritten_pictured_instruction_still_fails_closed() -> None:
    text = "Betrakta diagrammet."
    pictured = DocxChunk(
        "body:0001",
        "paragraph",
        text,
        text,
        images=(
            DocxImage(
                payload=b"review-probe-png",
                media_type="image/png",
                offset=0,
                marked_offset=0,
            ),
        ),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )
    instruction = _rewritten_instruction((pictured.anchor,))

    with pytest.raises(ValueError, match="instruction pictures have no faithful place"):
        instruction_paragraphs(instruction, {pictured.anchor: pictured})
