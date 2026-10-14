"""D4: the teacher-only marking guide never enters the student QTI package."""

import hashlib
import zipfile
from io import BytesIO
from uuid import uuid4

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)


def test_teacher_marking_guide_is_absent_from_every_qti_package_member() -> None:
    guide = "PRIVATE_SCORER_GUIDE_39_05_09: answer is photosynthesis <rubricBlock>"
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Biologiprov",
        origin=NativeExamDocumentOrigin(kind="created"),
        items=(
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(NativeParagraph(segments=(NativeTextSegment(text="Förklara processen."),)),),
                points=3,
                marking_guide=guide,
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=NativeItemReview(
                    state=NativeItemReviewState.REVIEW_COMPLETE,
                    parse_origin=NativeParseOrigin.TEACHER_CREATED,
                ),
            ),
        ),
    )
    package, _report = build_native_examnet_qti_package(
        document, package_name="biologiprov", qti_writer=ExamNetQtiPackageWriter()
    )
    with zipfile.ZipFile(BytesIO(package)) as archive:
        members = [archive.read(name) for name in archive.namelist()]
    assert members
    assert any("Förklara processen.".encode() in member for member in members)
    assert all(b"PRIVATE_SCORER_GUIDE_39_05_09" not in member for member in members)
    assert all(b"photosynthesis" not in member for member in members)
    assert all(b"rubricBlock" not in member for member in members)


def test_a_picture_retained_only_as_teacher_key_source_is_not_exported_to_students() -> None:
    payload = b"PRIVATE_FACIT_PICTURE_39_05_09"
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(NativeParagraph(segments=(NativeTextSegment(text="Förklara processen."),)),),
        points=3,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
        retry_source=NativeExamRetrySource(
            chunks=(
                NativeExamRetryChunk(
                    anchor="body:0001",
                    kind="paragraph",
                    text="Förklara processen.",
                    marked_text="Förklara processen.",
                ),
            ),
            key_chunks=(
                NativeExamRetryChunk(
                    anchor="body:0002",
                    kind="drawing",
                    text="",
                    marked_text="",
                    images=(NativeExamRetryImage(asset_id=asset_id, offset=0, marked_offset=0),),
                ),
            ),
            label_kind=NativeExamItemKind.FREE_TEXT,
        ),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Biologiprov",
        origin=NativeExamDocumentOrigin(kind="created"),
        items=(item,),
        assets=(
            NativeExamAsset(
                asset_id=asset_id,
                sha256=digest,
                media_type="image/png",
                byte_length=len(payload),
            ),
        ),
    )
    package, _report = build_native_examnet_qti_package(
        document,
        package_name="biologiprov",
        qti_writer=ExamNetQtiPackageWriter(),
        assets_by_id={asset_id: payload},
    )
    with zipfile.ZipFile(BytesIO(package)) as archive:
        assert all(not name.endswith((".png", ".jpg", ".jpeg")) for name in archive.namelist())
        assert all(payload not in archive.read(name) for name in archive.namelist())
