"""Shared builders for the native exam -> Exam.net QTI mapping tests."""

from uuid import uuid4
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import ExamNetQtiItem
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextMark,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeItemReview
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

ASSET_ID = "asset_0123456789abcdef"
ASSET_PAYLOAD = b"\x89PNG fake payload"


def tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def text(value: str, *marks: NativeTextMark) -> NativeTextSegment:
    return NativeTextSegment(text=value, marks=marks)


def paragraph(*segments: NativeSegment, heading_level: int | None = None) -> NativeParagraph:
    return NativeParagraph(segments=segments, heading_level=heading_level)


def document(
    *items: NativeExamItem,
    instructions: tuple[NativeParagraph, ...] = (),
    parents: tuple[NativeExamParent, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Formateringsprov",
        instructions=instructions,
        items=items,
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def serialize(item: ExamNetQtiItem) -> tuple[str, ElementTree.Element]:
    xml_text = serialize_qti_assessment_item(item).decode("utf-8")
    return xml_text, ElementTree.fromstring(xml_text)


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
    return (
        NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
    )
