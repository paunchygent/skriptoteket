"""Official course choice replaces source hints across all native export seams (D5)."""

from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest
from docx import Document

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    IMSMD_NAMESPACE,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_export_header import (
    exam_course_line,
    exam_export_header_lines,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamDocument,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeItemReviewState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    recorded_document,
    recorded_items,
)

_OFFICIAL = ExamCourseChoice(key="gy11:ENGENG05", name="Engelska 5")
_HINT = "Engelska, läsperiod 1"
_TITLE = "Omdöpt prov: läsförståelse"
_COURSE_CASES = (
    pytest.param(_OFFICIAL, _HINT, _OFFICIAL.name, id="choice-overrides-different-hint"),
    pytest.param(_OFFICIAL, None, _OFFICIAL.name, id="choice-without-hint"),
    pytest.param(None, _HINT, _HINT, id="unselected-retains-hint"),
    pytest.param(None, None, None, id="no-course-line"),
)


@pytest.mark.parametrize(("course", "hint", "expected"), _COURSE_CASES)
def test_course_line_selects_only_the_official_name_or_source_hint(
    course: ExamCourseChoice | None, hint: str | None, expected: str | None
) -> None:
    assert exam_course_line(NativeExamHeader(course=course, course_hint=hint)) == expected


def _exam(course: ExamCourseChoice | None, hint: str | None) -> NativeExamDocument:
    # Keep actual converted question content and keys from the recorded English exam.
    # Only teacher-owned metadata/review/points are changed for this export scenario.
    items = []
    for item, points in zip(recorded_items()[:2], (2.5, 3), strict=True):
        answer_key = item.answer_key
        if answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED:
            answer_key = answer_key.model_copy(
                update={"origin": NativeAnswerKeyOrigin.REVIEWED_ADVISORY}
            )
        items.append(
            item.model_copy(
                update={
                    "points": points,
                    "answer_key": answer_key,
                    "review": item.review.model_copy(
                        update={"state": NativeItemReviewState.REVIEW_COMPLETE}
                    ),
                }
            )
        )
    return recorded_document(items=tuple(items)).model_copy(
        update={
            "title": _TITLE,
            "header": NativeExamHeader(course=course, course_hint=hint, printed_total=99),
        }
    )


@pytest.mark.parametrize(("course", "hint", "expected"), _COURSE_CASES)
def test_qti_package_manifest_uses_course_choice_and_keeps_teacher_title(
    course: ExamCourseChoice | None, hint: str | None, expected: str | None
) -> None:
    package, _ = build_native_examnet_qti_package(
        _exam(course, hint), package_name="teacher-renamed", qti_writer=ExamNetQtiPackageWriter()
    )
    with ZipFile(BytesIO(package)) as archive:
        manifest = ET.fromstring(archive.read("imsmanifest.xml"))
        assessment = ET.fromstring(archive.read("assessment.xml"))
    ns = {"md": IMSMD_NAMESPACE}
    keywords = manifest.findall(".//md:general/md:keyword/md:string", ns)
    assert [node.text for node in keywords] == ([] if expected is None else [expected])
    assert manifest.findtext(".//md:general/md:title/md:string", namespaces=ns) == _TITLE
    assert assessment.attrib["title"] == _TITLE


@pytest.mark.parametrize(("course", "hint", "expected"), _COURSE_CASES)
def test_pdf_header_keeps_title_and_computed_total_but_replaces_raw_hint(
    course: ExamCourseChoice | None, hint: str | None, expected: str | None
) -> None:
    exam = _exam(course, hint)
    lines = (_TITLE, *((expected,) if expected is not None else ()), "Totalt: 5,5 poäng")
    assert exam_export_header_lines(exam) == lines
    pdf_plan = native_exam_to_pdf_document(exam)
    assert pdf_plan.html
    header_html = pdf_plan.html.split('<section class="exam-item">', 1)[0]
    for line in lines:
        assert line in header_html
    if course is not None:
        assert _HINT not in header_html


@pytest.mark.parametrize(("course", "hint", "expected"), _COURSE_CASES)
def test_docx_header_paragraphs_keep_title_and_computed_total_but_replace_raw_hint(
    course: ExamCourseChoice | None, hint: str | None, expected: str | None
) -> None:
    payload = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(
        _exam(course, hint)
    )
    paragraphs = Document(BytesIO(payload)).paragraphs
    expected_lines = [_TITLE, *([expected] if expected is not None else []), "Totalt: 5,5 poäng"]
    assert [paragraph.text for paragraph in paragraphs[: len(expected_lines)]] == expected_lines
    if course is not None:
        assert _HINT not in [paragraph.text for paragraph in paragraphs]
