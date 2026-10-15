"""A standalone gap-fill item places its gap where the body holds it.

Literal underscore runs in the global instructions or the question text are
answer lines, not gaps, and stay text in the exported item.
"""

import zipfile
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)


def _text(text: str) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))


def _local(node: ElementTree.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def test_standalone_gap_stays_in_its_paragraph_beside_literal_answer_lines() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            _text("Vilken stad är Sveriges huvudstad? ______"),
            NativeParagraph(heading_level=None, segments=(NativeGapSegment(gap_id="gap_001"),)),
        ),
        points=1,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=("Stockholm",)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.TEACHER_CREATED,
        ),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Huvudstäder",
        items=(item,),
        instructions=(_text("Namn: ______________ Klass: ________"),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )

    package, _report = build_native_examnet_qti_package(
        document,
        package_name="huvudstader",
        qti_writer=ExamNetQtiPackageWriter(),
    )

    with zipfile.ZipFile(BytesIO(package)) as archive:
        root = ElementTree.fromstring(archive.read("items/item_001.xml"))
    body = next(node for node in root.iter() if _local(node) == "qti-item-body")
    paragraphs = [node for node in body if _local(node) == "p"]
    texts = ["".join(paragraph.itertext()).strip() for paragraph in paragraphs]
    interactions = [
        [_local(child) for child in paragraph if _local(child) == "qti-text-entry-interaction"]
        for paragraph in paragraphs
    ]
    assert texts == [
        "Namn: ______________ Klass: ________",
        "Vilken stad är Sveriges huvudstad? ______",
        "",
    ]
    assert interactions == [[], [], ["qti-text-entry-interaction"]]
