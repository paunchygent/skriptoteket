"""Shared builders for the native exam -> Exam.net QTI mapping tests."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeItemReview
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

ASSET_ID = "asset_0123456789abcdef"
ASSET_PAYLOAD = b"\x89PNG fake payload"


def review_complete() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.TEACHER_CREATED,
    )


def document_of(
    items: tuple[NativeExamItem, ...],
    assets: tuple[NativeExamAsset, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov på svenska",
        items=items,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def text_body(text: str) -> tuple[NativeParagraph, ...]:
    return (NativeParagraph(segments=(NativeTextSegment(text=text),)),)
