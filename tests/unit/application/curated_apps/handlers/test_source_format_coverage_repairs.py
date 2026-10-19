"""Native admission keeps a marked free-text prefix and every source heading level."""

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    aligned_native_item,
    assemble_build_result,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit


def _as_text(segment: NativeSegment) -> NativeTextSegment:
    assert isinstance(segment, NativeTextSegment)
    return segment


def _chunk(anchor, text, runs, heading=None):
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=tuple(runs),
        paragraphs=(DocxSourceParagraph(0, text, heading),),
    )


def _produced(text, anchors, printed_label=None):
    return ProducedItem(
        source_anchors=anchors,
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
        printed_label=printed_label,
    )


def test_native_item_rebuilds_a_marked_free_text_prefix_from_source():
    text = "Safety. Do not mix acids."
    safety = _chunk(
        "body:0001",
        text,
        (DocxSourceRun(0, "Safety.", ("bold",)), DocxSourceRun(7, text[7:], ())),
    )
    item = aligned_native_item(
        _produced("Do not mix acids.", (safety.anchor,)),
        chunks=(safety,),
        language="en",
        foreign_chunks=(),
    ).item
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert body_plain_text(item.body) == text
    assert _as_text(item.body[0].segments[0]).text == "Safety."
    assert _as_text(item.body[0].segments[0]).marks == ("bold",)


def test_assembled_item_keeps_an_omitted_size_heading():
    heading = _chunk(
        "body:0001",
        "Read this section carefully.",
        (DocxSourceRun(0, "Read this section carefully.", ()),),
        2,
    )
    question = _chunk(
        "body:0002", "Answer the question.", (DocxSourceRun(0, "Answer the question.", ()),)
    )
    item = aligned_native_item(
        _produced("Answer the question.", (heading.anchor, question.anchor)),
        chunks=(heading, question),
        language="en",
        foreign_chunks=(),
    )
    result = assemble_build_result(
        document_id=uuid4(),
        filename="heading.docx",
        source_sha256="a" * 64,
        chunks=(heading, question),
        accepted=((item, (heading.anchor, question.anchor)),),
        review_reasons={},
    )
    body = result.document.items[0].body
    assert [paragraph.heading_level for paragraph in body] == [2, None]
    assert body_plain_text(body) == "Read this section carefully.\nAnswer the question."
