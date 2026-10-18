"""Stored retry-chunk round-trip: source formatting, pictures and document persistence.

TASK-SKRIPT-39-09-08: a saved retry source rebuilds the DOCX reader's marks, heading
levels and picture references, so one-question retry keeps the source formatting across
save and reopen.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetryParagraph,
    NativeExamRetryRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    chunk_from_record,
    chunk_record,
    own_chunks,
    question_retry_source,
)
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

pytestmark = pytest.mark.unit

_ASSET_ID = "asset_0123456789abcdef"


def _item(item_id: str, sequence: int) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(NativeTextSegment(text="Fråga?", marks=()),),
            ),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
        ),
        source_anchor="body:0001",
    )


def _document(items: tuple[NativeExamItem, ...]) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def test_chunk_record_keeps_picture_references_and_rebuilds_from_saved_payloads():
    image = DocxImage(
        payload=b"png-bytes",
        media_type="image/png",
        offset=4,
        marked_offset=6,
        width=120,
        height=80,
    )
    chunk = DocxChunk(
        anchor="body:0007",
        kind="drawing",
        text="abcd",
        marked_text="abcd<i>x</i>",
        images=(image,),
        runs=(
            DocxSourceRun(offset=0, text="ab", marks=("bold", "italic")),
            DocxSourceRun(offset=2, text="cd", marks=()),
        ),
        paragraphs=(DocxSourceParagraph(offset=0, text="abcd", heading_level=2),),
    )

    record = chunk_record(chunk)
    assert record.images == (
        NativeExamRetryImage(asset_id=image.asset_id, offset=4, marked_offset=6),
    )
    assert record.runs == (
        NativeExamRetryRun(offset=0, text="ab", marks=("bold", "italic")),
        NativeExamRetryRun(offset=2, text="cd", marks=()),
    )
    assert record.paragraphs == (NativeExamRetryParagraph(offset=0, text="abcd", heading_level=2),)

    assets = {
        image.asset_id: NativeExamAsset(
            asset_id=image.asset_id,
            sha256="b" * 64,
            media_type="image/png",
            byte_length=len(image.payload),
            width=120,
            height=80,
        )
    }
    rebuilt = chunk_from_record(record, assets=assets, payloads={image.asset_id: image.payload})

    assert rebuilt == chunk


def test_stored_runs_and_paragraphs_survive_a_document_round_trip():
    chunk = DocxChunk(
        anchor="body:0001",
        kind="paragraph",
        text="Fet och kursiv",
        marked_text="<b>Fet</b> och <i>kursiv</i>",
        runs=(
            DocxSourceRun(offset=0, text="Fet", marks=("bold",)),
            DocxSourceRun(offset=3, text=" och ", marks=()),
            DocxSourceRun(offset=8, text="kursiv", marks=("italic", "underline")),
        ),
        paragraphs=(DocxSourceParagraph(offset=0, text="Fet och kursiv", heading_level=1),),
    )
    source = question_retry_source(
        own_anchors=("body:0001",),
        owned_context_anchors=(),
        key_anchors=(),
        read_anchors=frozenset(),
        chunks=(chunk,),
        label_kind=NativeExamItemKind.FREE_TEXT,
    )
    item = _item("item_001", 1).model_copy(update={"retry_source": source})
    document = _document((item,))

    restored = NativeExamDocument.model_validate_json(document.model_dump_json())
    stored_source = restored.items[0].retry_source
    assert stored_source is not None
    rebuilt = own_chunks(stored_source, assets={}, payloads={})

    assert rebuilt[0].runs == chunk.runs
    assert rebuilt[0].paragraphs == chunk.paragraphs


def test_a_picture_reference_without_saved_bytes_fails_closed():
    record = NativeExamRetryChunk(
        anchor="body:0007",
        kind="drawing",
        text="",
        marked_text="",
        runs=(),
        paragraphs=(),
        images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=0, marked_offset=0),),
    )

    with pytest.raises(KeyError):
        chunk_from_record(record, assets={}, payloads={})
