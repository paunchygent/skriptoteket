"""Header metadata stays outside QTI items and prints once in document exports."""

import json
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest
from docx import Document

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamHeader,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)

_TITLE = "Språkprov & analys <avslutning>"
_COURSE = "Svenska 2 & språk <fördjupning>"
_LOM = {"lom": "http://ltsc.ieee.org/xsd/LOM"}


def _document(
    *,
    course_hint: str | None = _COURSE,
    points: tuple[int | float | None, ...] = (4, 3.5),
) -> NativeExamDocument:
    items = tuple(
        make_free_text_item(sequence=index, item_id=f"item_{index:03d}").model_copy(
            update={"points": value}
        )
        for index, value in enumerate(points, start=1)
    )
    return make_document(*items).model_copy(
        update={
            "title": _TITLE,
            "header": NativeExamHeader(course_hint=course_hint, printed_total=99),
        }
    )


class _BodyText(HTMLParser):
    """Read visible body text, excluding the PDF HTML's head/title metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body":
            self.in_body = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "body":
            self.in_body = False

    def handle_data(self, data: str) -> None:
        if self.in_body:
            self.parts.append(data)


@pytest.mark.parametrize("course_hint", [_COURSE, None])
def test_qti_manifest_carries_escaped_metadata_without_leaking_into_items(
    course_hint: str | None,
) -> None:
    document = _document(course_hint=course_hint)
    package, report = build_native_examnet_qti_package(
        document,
        package_name="different-download-name",
        qti_writer=ExamNetQtiPackageWriter(),
    )

    assert json.loads(report)["package_status"] == "passed"
    with zipfile.ZipFile(BytesIO(package)) as archive:
        manifest = ET.fromstring(archive.read("imsmanifest.xml"))
        metadata = next(node for node in manifest if node.tag.rsplit("}", 1)[-1] == "metadata")
        assert (
            metadata.findtext("lom:lom/lom:general/lom:title/lom:string", namespaces=_LOM) == _TITLE
        )
        title = metadata.find("lom:lom/lom:general/lom:title/lom:string", _LOM)
        assert title is not None and title.attrib["language"] == "sv"
        keyword_elements = metadata.findall("lom:lom/lom:general/lom:keyword", _LOM)
        assert len(keyword_elements) == (0 if course_hint is None else 1)
        keywords = metadata.findall("lom:lom/lom:general/lom:keyword/lom:string", _LOM)
        assert [keyword.text for keyword in keywords] == ([] if course_hint is None else [_COURSE])
        assert all(keyword.attrib["language"] == "sv" for keyword in keywords)
        assessment = ET.fromstring(archive.read(EXAMNET_QTI_ASSESSMENT_TEST_PATH))
        assert assessment.attrib["title"] == _TITLE
        item_paths = [
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        ]
        assert len(item_paths) == len(document.items)
        for path in item_paths:
            item = ET.fromstring(archive.read(path))
            text = " ".join(item.itertext())
            assert _COURSE not in text
            assert _TITLE not in text
            assert "Totalt:" not in text
            assert "99" not in text


@pytest.mark.parametrize("course_hint", [_COURSE, None])
def test_pdf_visible_header_is_generated_once_outside_items(course_hint: str | None) -> None:
    rendered = native_exam_to_pdf_document(_document(course_hint=course_hint))

    assert rendered.status is DigiExamExamNetPdfStatus.SUCCESS
    parser = _BodyText()
    parser.feed(rendered.html)
    visible = "\n".join(parser.parts)
    assert visible.count(_TITLE) == 1
    assert visible.count("Totalt: 7,5 poäng") == 1
    assert visible.count(_COURSE) == (0 if course_hint is None else 1)
    assert "99" not in visible
    assert "7.5" not in visible
    for section in rendered.html.split('<section class="exam-item">')[1:]:
        assert "Totalt:" not in section
        assert "Svenska 2" not in section


@pytest.mark.parametrize(
    ("points", "expected_total"),
    [((4, None, 3.5), "Totalt: 7,5 poäng"), ((4, 3), "Totalt: 7 poäng"), ((None,), None)],
)
@pytest.mark.parametrize("course_hint", [_COURSE, None])
def test_docx_header_uses_item_sum_not_printed_total_and_omits_unavailable_total(
    points: tuple[int | float | None, ...], expected_total: str | None, course_hint: str | None
) -> None:
    content = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(
        _document(course_hint=course_hint, points=points)
    )
    paragraphs = [paragraph.text for paragraph in Document(BytesIO(content)).paragraphs]

    expected_header = [_TITLE]
    if course_hint is not None:
        expected_header.append(course_hint)
    if expected_total is not None:
        expected_header.append(expected_total)
    assert paragraphs[: len(expected_header)] == expected_header
    assert paragraphs.count(_TITLE) == 1
    assert paragraphs.count(_COURSE) == (0 if course_hint is None else 1)
    assert [text for text in paragraphs if text.startswith("Totalt:")] == (
        [] if expected_total is None else [expected_total]
    )
    assert not any("99" in text for text in paragraphs)
