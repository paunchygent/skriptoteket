"""Fail-closed Exam.net QTI package build from the native exam document."""

import json
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_extractor,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

PythonDocxExamExtractor = exam_workspace_docx_extractor.PythonDocxExamExtractor

_FIXTURE = Path(
    "tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx"
)


def _reviewed(document: NativeExamDocument) -> NativeExamDocument:
    """Flip every item to an export-ready review/trust state via model_copy."""
    items = []
    for item in document.items:
        answer_key = item.answer_key
        if answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED:
            answer_key = answer_key.model_copy(
                update={"origin": NativeAnswerKeyOrigin.REVIEWED_ADVISORY}
            )
        items.append(
            item.model_copy(
                update={
                    "review": item.review.model_copy(
                        update={"state": NativeItemReviewState.REVIEW_COMPLETE}
                    ),
                    "answer_key": answer_key,
                    "points": item.points if item.points is not None else 1,
                }
            )
        )
    return document.model_copy(update={"items": tuple(items)})


@pytest.fixture(scope="module")
def extracted_document() -> NativeExamDocument:
    return (
        PythonDocxExamExtractor()
        .extract(document_id=uuid4(), filename=_FIXTURE.name, content=_FIXTURE.read_bytes())
        .document
    )


@pytest.fixture(scope="module")
def reviewed_document(extracted_document: NativeExamDocument) -> NativeExamDocument:
    return _reviewed(extracted_document)


class TestExportGate:
    def test_export_blockers_raise_with_blocker_details(
        self, extracted_document: NativeExamDocument
    ) -> None:
        with pytest.raises(DomainError) as exc_info:
            build_native_examnet_qti_package(
                extracted_document,
                package_name="grammatik-omprov",
                qti_writer=ExamNetQtiPackageWriter(),
            )

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        blockers = exc_info.value.details["blockers"]
        assert isinstance(blockers, list) and blockers
        assert all({"item_id", "reason"} <= set(blocker) for blocker in blockers)

    def test_absent_answer_key_blocks_before_planning(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Fyll i: "),
                        NativeGapSegment(gap_id="gap_001"),
                    )
                ),
            ),
            points=2,
            gaps=(NativeGap(gap_id="gap_001"),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
            review=NativeItemReview(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.TEACHER_CREATED,
            ),
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Prov utan facit",
            items=(item,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        with pytest.raises(DomainError) as exc_info:
            build_native_examnet_qti_package(
                document,
                package_name="prov-utan-facit",
                qti_writer=ExamNetQtiPackageWriter(),
            )

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["blockers"] == [
            {"item_id": "item_001", "reason": "missing_answer_key"}
        ]


class TestFullPackageBuild:
    @pytest.fixture(scope="class")
    def built(self, reviewed_document: NativeExamDocument) -> tuple[bytes, bytes]:
        return build_native_examnet_qti_package(
            reviewed_document,
            package_name="grammatik-omprov",
            qti_writer=ExamNetQtiPackageWriter(),
        )

    def test_validation_report_passed_and_binds_package(self, built: tuple[bytes, bytes]) -> None:
        package_bytes, report_bytes = built
        report = json.loads(report_bytes)

        assert report["package_status"] == "passed"
        assert report["package_filename"] == "grammatik-omprov.zip"
        assert report["package_sha256"] is not None

    def test_package_zip_contains_manifest_test_and_item_xml(
        self,
        built: tuple[bytes, bytes],
        reviewed_document: NativeExamDocument,
    ) -> None:
        package_bytes, _ = built
        with zipfile.ZipFile(BytesIO(package_bytes)) as archive:
            names = set(archive.namelist())

        assert "imsmanifest.xml" in names
        assert EXAMNET_QTI_ASSESSMENT_TEST_PATH in names
        for item in reviewed_document.items:
            assert f"items/{item.item_id}.xml" in names
