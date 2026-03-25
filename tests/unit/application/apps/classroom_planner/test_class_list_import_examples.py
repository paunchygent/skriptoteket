"""Example-corpus regression tests for class-list import.

Purpose:
  Verify the import pipeline against the real sample files committed under
  `data/class_list_example_inputs`.

Relationships:
  - Exercises `CreateClassListImportPreviewHandler` together with the concrete
    extractor and parser implementations.
  - Verifies both the local PDF fast path and the Sir Convert fallback path.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from openpyxl import Workbook

from skriptoteket.application.curated_apps.classroom_planner.handlers.imports import (
    CreateClassListImportPreviewHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.import_heuristics import (
    ClassListHeuristicParser,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner import (
    class_list_document_extractor as class_list_document_extractor_module,
)
from skriptoteket.protocols.classroom_planner_imports import ExtractedDocumentText
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertJobV2,
    SirConvertSubmitRequestV2,
    SirConvertSubmittedJobV2,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
)

_EXAMPLE_ROOT = Path(__file__).resolve().parents[5] / "data" / "class_list_example_inputs"
_EXPECTED_CLASS_NAME = "SA24D"
_EXPECTED_STUDENT_COUNT = 31
_EXPECTED_FIRST_STUDENT = "Kerstin Aitman"
ClassListDocumentExtractor = class_list_document_extractor_module.ClassListDocumentExtractor


class RecordingSirConvertClient:
    def __init__(self, *, text_response: str) -> None:
        self._text_response = text_response
        self.calls: list[tuple[str, bytes, str | None]] = []

    async def extract_text_direct(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> str:
        self.calls.append((filename, file_bytes, correlation_id))
        return self._text_response

    async def submit_job(
        self,
        *,
        request: SirConvertSubmitRequestV2,
    ) -> SirConvertSubmittedJobV2:
        del request
        raise AssertionError("submit_job should not be called in these example-corpus tests.")

    async def get_job(self, job_id: str, *, correlation_id: str | None) -> SirConvertJobV2:
        del job_id, correlation_id
        raise AssertionError("get_job should not be called in these example-corpus tests.")

    async def download_artifact(
        self, job_id: str, *, correlation_id: str | None
    ) -> SirConvertArtifactOutcomeV2:
        del job_id, correlation_id
        raise AssertionError(
            "download_artifact should not be called in these example-corpus tests."
        )

    async def create_webhook_subscription(
        self,
        *,
        callback_url: str,
        event_types: list[str],
        correlation_id: str | None,
    ) -> SirConvertWebhookSubscriptionV2:
        del callback_url, event_types, correlation_id
        raise AssertionError(
            "create_webhook_subscription should not be called in these example-corpus tests."
        )

    async def list_webhook_subscriptions(
        self,
        *,
        correlation_id: str | None,
    ) -> list[SirConvertWebhookSubscriptionSummaryV2]:
        del correlation_id
        raise AssertionError(
            "list_webhook_subscriptions should not be called in these example-corpus tests."
        )

    async def delete_webhook_subscription(
        self,
        subscription_id: str,
        *,
        correlation_id: str | None,
    ) -> None:
        del subscription_id, correlation_id
        raise AssertionError(
            "delete_webhook_subscription should not be called in these example-corpus tests."
        )


class ScriptedPdfTextExtractor:
    def __init__(self, *, local_text: str, upstream_text: str) -> None:
        self._local_text = local_text
        self._upstream_text = upstream_text
        self.calls: list[bool] = []

    async def extract_text(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
        correlation_id: str | None = None,
        allow_local_pdf_fast_path: bool = True,
    ) -> ExtractedDocumentText | None:
        del file_content, file_name, content_type, correlation_id
        self.calls.append(allow_local_pdf_fast_path)
        if allow_local_pdf_fast_path:
            return ExtractedDocumentText(
                text=self._local_text,
                source="local_pdf_fast_path",
            )
        return ExtractedDocumentText(
            text=self._upstream_text,
            source="upstream_pdf",
        )

    async def extract_rows(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
        correlation_id: str | None = None,
    ) -> list[list[str]] | None:
        del file_content, file_name, content_type, correlation_id
        return None


def _build_handler(
    *, pdf_text_response: str
) -> tuple[CreateClassListImportPreviewHandler, RecordingSirConvertClient]:
    sir_convert = RecordingSirConvertClient(text_response=pdf_text_response)
    extractor = ClassListDocumentExtractor(settings=Settings(), sir_convert=sir_convert)
    handler = CreateClassListImportPreviewHandler(
        extractor=extractor,
        parser=ClassListHeuristicParser(),
    )
    return handler, sir_convert


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("file_name", "content_type"),
    [
        ("sa24d_klasslista_komma.txt", "text/plain"),
        ("sa24d_klasslista_tab.txt", "text/plain"),
        ("sa24d_klasslista.excel.xls", "application/vnd.ms-excel"),
    ],
)
async def test_import_preview_parses_example_text_and_xls_files(
    file_name: str, content_type: str
) -> None:
    handler, _ = _build_handler(pdf_text_response="")
    file_content = (_EXAMPLE_ROOT / file_name).read_bytes()

    preview = await handler.handle(
        file_content=file_content,
        file_name=file_name,
        content_type=content_type,
    )

    assert preview.suggested_class_name == _EXPECTED_CLASS_NAME
    assert len(preview.parsed_students) == _EXPECTED_STUDENT_COUNT
    assert preview.parsed_students[0].full_name == _EXPECTED_FIRST_STUDENT


@pytest.mark.asyncio
async def test_import_preview_parses_example_pdf_file_via_local_fast_path() -> None:
    pdf_file = _EXAMPLE_ROOT / "sa24d_klasslista.pdf"
    pdf_text = "Export metadata only"
    handler, sir_convert = _build_handler(pdf_text_response=pdf_text)

    preview = await handler.handle(
        file_content=pdf_file.read_bytes(),
        file_name=pdf_file.name,
        content_type="application/pdf",
        correlation_id="corr-1",
    )

    assert preview.suggested_class_name == _EXPECTED_CLASS_NAME
    assert len(preview.parsed_students) == _EXPECTED_STUDENT_COUNT
    assert preview.parsed_students[0].full_name == _EXPECTED_FIRST_STUDENT
    assert sir_convert.calls == [(pdf_file.name, pdf_file.read_bytes(), "corr-1")]


@pytest.mark.asyncio
async def test_import_preview_falls_back_to_sir_convert_when_local_pdf_text_is_unavailable() -> (
    None
):
    pdf_bytes = b"%PDF-1.4\nthis-is-not-a-valid-pdf\n%%EOF"
    pdf_text = (_EXAMPLE_ROOT / "sa24d_klasslista_tab.txt").read_text(encoding="utf-8")
    handler, sir_convert = _build_handler(pdf_text_response=pdf_text)

    preview = await handler.handle(
        file_content=pdf_bytes,
        file_name="broken.pdf",
        content_type="application/pdf",
        correlation_id="corr-fallback",
    )

    assert preview.suggested_class_name == _EXPECTED_CLASS_NAME
    assert len(preview.parsed_students) == _EXPECTED_STUDENT_COUNT
    assert preview.parsed_students[0].full_name == _EXPECTED_FIRST_STUDENT
    assert sir_convert.calls == [("broken.pdf", pdf_bytes, "corr-fallback")]


@pytest.mark.asyncio
async def test_import_preview_retries_upstream_when_local_pdf_text_is_not_parseable() -> None:
    extractor = ScriptedPdfTextExtractor(
        local_text="Klasslista metadata export",
        upstream_text=(_EXAMPLE_ROOT / "sa24d_klasslista_tab.txt").read_text(encoding="utf-8"),
    )
    handler = CreateClassListImportPreviewHandler(
        extractor=extractor,
        parser=ClassListHeuristicParser(),
    )

    preview = await handler.handle(
        file_content=b"%PDF-1.7",
        file_name="metadata-only.pdf",
        content_type="application/pdf",
        correlation_id="corr-upstream-retry",
    )

    assert extractor.calls == [True, False]
    assert preview.suggested_class_name == _EXPECTED_CLASS_NAME
    assert len(preview.parsed_students) == _EXPECTED_STUDENT_COUNT
    assert preview.parsed_students[0].full_name == _EXPECTED_FIRST_STUDENT


@pytest.mark.asyncio
async def test_import_preview_prefers_upstream_when_local_pdf_text_is_partial() -> None:
    extractor = ScriptedPdfTextExtractor(
        local_text="SA24D\n1 Aitman, Kerstin\n2 Andersson, Sofia",
        upstream_text=(_EXAMPLE_ROOT / "sa24d_klasslista_tab.txt").read_text(encoding="utf-8"),
    )
    handler = CreateClassListImportPreviewHandler(
        extractor=extractor,
        parser=ClassListHeuristicParser(),
    )

    preview = await handler.handle(
        file_content=b"%PDF-1.7",
        file_name="partial-local.pdf",
        content_type="application/pdf",
        correlation_id="corr-partial-upstream-retry",
    )

    assert extractor.calls == [True, False]
    assert preview.suggested_class_name == _EXPECTED_CLASS_NAME
    assert len(preview.parsed_students) == _EXPECTED_STUDENT_COUNT
    assert preview.parsed_students[0].full_name == _EXPECTED_FIRST_STUDENT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("file_name", "file_content", "expected_names"),
    [
        (
            "family-first.csv",
            b"Andersson,Alice\nBerglund,Bob\n",
            ["Alice Andersson", "Bob Berglund"],
        ),
        (
            "given-first.tsv",
            b"Alice\tAndersson\nBob\tBerglund\n",
            ["Alice Andersson", "Bob Berglund"],
        ),
    ],
)
async def test_import_preview_keeps_two_column_name_order_without_numeric_index(
    file_name: str,
    file_content: bytes,
    expected_names: list[str],
) -> None:
    handler, _ = _build_handler(pdf_text_response="")

    preview = await handler.handle(
        file_content=file_content,
        file_name=file_name,
        content_type="text/plain",
    )

    assert [student.full_name for student in preview.parsed_students] == expected_names


@pytest.mark.asyncio
async def test_import_preview_parses_indexed_split_name_xlsx_rows() -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Nr", "Efternamn", "Förnamn"])
    sheet.append(["1", "Andersson", "Alice"])
    sheet.append(["2", "Berglund", "Bob"])

    buffer = io.BytesIO()
    workbook.save(buffer)

    handler, _ = _build_handler(pdf_text_response="")
    preview = await handler.handle(
        file_content=buffer.getvalue(),
        file_name="split-name-columns.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert [student.full_name for student in preview.parsed_students] == [
        "Alice Andersson",
        "Bob Berglund",
    ]
