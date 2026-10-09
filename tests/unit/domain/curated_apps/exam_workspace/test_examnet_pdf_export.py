"""Native exam -> Exam.net PDF document plan tests (real fixture + render proof)."""

from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeItemReviewState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_extractor,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
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
def reviewed_document() -> NativeExamDocument:
    extracted = PythonDocxExamExtractor().extract(
        document_id=uuid4(), filename=_FIXTURE.name, content=_FIXTURE.read_bytes()
    )
    return _reviewed(extracted.document)


class TestPdfDocumentPlan:
    def test_reviewed_fixture_builds_a_success_document(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        document = native_exam_to_pdf_document(reviewed_document)

        assert document.status is DigiExamExamNetPdfStatus.SUCCESS
        assert "Omprov: grammatik och språkstrukturer" in document.html
        assert "Fråga 1" in document.html
        assert "Frastyp:" in document.html
        assert '<span class="gap-placeholder">[____]</span>' in document.html
        assert document.asset_files == ()

    def test_missing_points_blocks_the_document(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        first_item = reviewed_document.items[0].model_copy(update={"points": None})
        broken = reviewed_document.model_copy(
            update={"items": (first_item, *reviewed_document.items[1:])}
        )

        document = native_exam_to_pdf_document(broken)

        assert document.status is DigiExamExamNetPdfStatus.BLOCKED
        assert document.html == ""
        assert any(
            warning.code is DigiExamExamNetPdfWarningCode.MISSING_POINT_VALUE
            for warning in document.warnings
        )


class TestPdfRendering:
    def test_weasyprint_renders_non_empty_pdf_bytes(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        document = native_exam_to_pdf_document(reviewed_document)

        pdf_bytes = WeasyPrintExamNetPdfRenderer().render_pdf(document=document)

        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000
