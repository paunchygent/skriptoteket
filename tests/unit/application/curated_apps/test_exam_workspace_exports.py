"""Fail-closed Exam.net QTI package build from the native exam document."""

import json
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import review_source_item
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
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
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import make_document

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


def _source_fallback_document() -> NativeExamDocument:
    chunk = DocxChunk(
        anchor="body:0001",
        kind="paragraph",
        text="Förklara. (2 p)",
        marked_text="Förklara. (2 p)",
    )
    return make_document(review_source_item((chunk,), "Frågan kunde inte konverteras."))


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
    return NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())


@pytest.fixture(scope="module")
def reviewed_document(extracted_document: NativeExamDocument) -> NativeExamDocument:
    return _reviewed(extracted_document)


class TestExportGate:
    def test_export_blockers_raise_with_blocker_details(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            build_native_examnet_qti_package(
                _source_fallback_document(),
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
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Fyll i: ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
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

    def test_blank_prompt_is_a_gate_blocker_and_refuses_the_package(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(
                NativeParagraph(
                    heading_level=None, segments=(NativeTextSegment(text=" ", marks=()),)
                ),
            ),
            points=2,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=NativeItemReview(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.TEACHER_CREATED,
            ),
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Prov med tom fråga",
            items=(item,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )
        assert [(b.item_id, b.reason) for b in native_export_blockers(document)] == [
            ("item_001", "empty_question_text")
        ]

        with pytest.raises(DomainError) as exc_info:
            build_native_examnet_qti_package(
                document,
                package_name="prov-tom-fraga",
                qti_writer=ExamNetQtiPackageWriter(),
            )

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.message == "The exam document is not ready for QTI export."
        assert exc_info.value.details == {
            "blockers": [{"item_id": "item_001", "reason": "empty_question_text"}]
        }


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

    def test_assessment_title_is_exam_title_not_package_name(
        self,
        built: tuple[bytes, bytes],
        reviewed_document: NativeExamDocument,
    ) -> None:
        package_bytes, _ = built
        with zipfile.ZipFile(BytesIO(package_bytes)) as archive:
            root = ElementTree.fromstring(archive.read(EXAMNET_QTI_ASSESSMENT_TEST_PATH))
            manifest = archive.read("imsmanifest.xml").decode("utf-8")

        titles = {element.get("title") for element in root.iter() if element.get("title")}
        assert titles == {reviewed_document.title}
        assert "grammatik-omprov" not in titles
        assert "grammatik-omprov" not in manifest

    def test_special_characters_in_the_exam_title_are_escaped(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        def assessment_title(title: str) -> str | None:
            document = reviewed_document.model_copy(update={"title": title})
            package_bytes, _ = build_native_examnet_qti_package(
                document, package_name="grammatik-omprov", qti_writer=ExamNetQtiPackageWriter()
            )
            with zipfile.ZipFile(BytesIO(package_bytes)) as archive:
                return ElementTree.fromstring(archive.read(EXAMNET_QTI_ASSESSMENT_TEST_PATH)).get(
                    "title"
                )

        assert assessment_title('Prov <A> & "B"') == 'Prov <A> & "B"'

    def test_title_without_letters_or_digits_is_refused_not_replaced_by_the_package_name(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        for title in ("   ", "?!..."):
            document = reviewed_document.model_copy(update={"title": title})
            with pytest.raises(DomainError) as exc_info:
                build_native_examnet_qti_package(
                    document,
                    package_name="grammatik-omprov",
                    qti_writer=ExamNetQtiPackageWriter(),
                )
            assert exc_info.value.details == {
                "blockers": [{"item_id": None, "reason": "title_without_text"}]
            }
