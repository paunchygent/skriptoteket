"""A size-derived answer-line heading never returns to the imported body (W10, R2).

A Normal-style DOCX answer-line paragraph with a larger font is marked by the real
chunker as a size-derived heading. Heading restoration must still exclude it as
answer space, while a real larger-font heading is still restored.
"""

import io

from docx import Document
from docx.shared import Pt

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)


def _chunked(prompt: str, second: str) -> tuple[DocxChunk, ...]:
    source = Document()
    prompt_run = source.add_paragraph().add_run(prompt)
    prompt_run.font.size = Pt(11)
    second_run = source.add_paragraph().add_run(second)
    second_run.font.size = Pt(22)
    second_run.underline = True
    stream = io.BytesIO()
    source.save(stream)
    return PythonDocxExamChunker().chunk(content=stream.getvalue())


def _paragraph(text: str) -> ProducedParagraph:
    return ProducedParagraph(
        segments=(ProducedSegment(kind="text", text=text, accepted_values=()),)
    )


def _produced(*texts: str) -> ProducedItem:
    return ProducedItem(
        source_anchors=("body:0001", "body:0002"),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.FREE_TEXT,
        printed_label=None,
        key_source=None,
        facit_text=None,
        body=tuple(_paragraph(text) for text in texts),
        points=1,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )


def test_a_larger_font_answer_line_marked_as_heading_stays_out_of_the_body() -> None:
    chunks = _chunked("Förklara.", "_____")

    assert chunks[1].paragraphs[0].heading_level is not None

    aligned = aligned_native_item(_produced("Förklara.", "_____"), chunks=chunks, language="sv")

    assert body_plain_text(aligned.item.body) == "Förklara."


def test_a_larger_font_real_heading_is_still_restored() -> None:
    chunks = _chunked("Förklara.", "Del A")

    assert chunks[1].paragraphs[0].heading_level is not None

    aligned = aligned_native_item(_produced("Förklara."), chunks=chunks, language="sv")

    assert body_plain_text(aligned.item.body) == "Förklara.\nDel A"
