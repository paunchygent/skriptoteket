"""Document Converter single-file browser proof helpers.

Domain purpose:
    Verify the authenticated Document Converter file-conversion lane in the
    live browser, especially compact ordering, source inference, and mode-local
    result ownership.

Relationships:
    Called by `scripts/authenticated_home_work_apps.py` during the compact
    Document Converter route proof.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

JsonObject = dict[str, object]


def assert_document_converter_single_file_compact_route(
    page: Page,
    *,
    artifact_dir: Path,
) -> JsonObject:
    """Prove compact single-file conversion behavior on the live route."""
    route = page.locator('main[aria-label="Dokumentkonverterare"]')
    expect(route).to_be_visible()

    route.locator('[data-test="document-converter-mode-single"]').click()
    source_column = route.get_by_test_id("document-converter-source-column")
    operations_column = route.get_by_test_id("document-converter-operations-column")
    preview_column = route.get_by_test_id("document-converter-preview-column")
    expect(source_column).to_be_visible()
    expect(operations_column).to_be_visible()
    _assert_compact_order(source_column=source_column, operations_column=operations_column)

    single_file_input = route.get_by_test_id("document-converter-single-file-input")
    accept_value = single_file_input.get_attribute("accept") or ""
    required_extensions = (".html", ".htm", ".docx", ".md", ".markdown", ".pdf")
    missing_extensions = [
        extension for extension in required_extensions if extension not in accept_value
    ]
    if missing_extensions:
        raise AssertionError(
            "Document Converter single-file picker did not accept all source formats: "
            f"{missing_extensions!r} from {accept_value!r}."
        )

    pdf_path = _write_pdf_probe(artifact_dir)
    single_file_input.set_input_files(str(pdf_path))
    expect(route.locator('[data-test="document-converter-source-pdf"]')).to_have_attribute(
        "aria-checked",
        "true",
    )
    expect(route.locator('[data-test="document-converter-output-md"]')).to_have_attribute(
        "aria-checked",
        "true",
    )

    html_path = _write_html_probe(artifact_dir)
    single_file_input.set_input_files(str(html_path))
    expect(route.locator('[data-test="document-converter-source-html"]')).to_have_attribute(
        "aria-checked",
        "true",
    )
    if (
        route.locator('[data-test="document-converter-output-pdf"]').get_attribute("aria-checked")
        != "true"
    ):
        route.locator('[data-test="document-converter-output-pdf"]').click()
    expect(route.locator('[data-test="document-converter-output-pdf"]')).to_have_attribute(
        "aria-checked",
        "true",
    )
    upload_row = source_column.locator(".dc-source-row").filter(has_text="single-file-proof.html")
    expect(upload_row).to_be_visible()

    route.get_by_test_id("document-converter-source-remove-0").click()
    expect(upload_row).to_have_count(0)
    expect(source_column.locator(".dc-source-empty")).to_have_text(
        "Välj en fil som du vill konvertera."
    )

    single_file_input.set_input_files(str(html_path))
    with page.expect_response(
        lambda response: (
            "/api/v1/apps/documents.conversion_hub/document-converter/jobs" in response.url
            and response.request.method == "POST"
        ),
        timeout=45_000,
    ) as submit_response_info:
        route.get_by_test_id("document-converter-start-single-file").click()
    submit_response = submit_response_info.value
    if submit_response.status != 200:
        response_path = artifact_dir / "document-converter-single-file-submit-response.json"
        response_path.write_text(
            json.dumps(
                {
                    "body": submit_response.text(),
                    "headers": dict(submit_response.headers),
                    "status": submit_response.status,
                    "url": submit_response.url,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        raise AssertionError(
            "Document Converter single-file submit failed with "
            f"{submit_response.status}. See {response_path}."
        )

    expect(preview_column.get_by_test_id("document-converter-pdf-frame")).to_be_visible(
        timeout=45_000
    )
    expect(operations_column.get_by_text("PDF klart för granskning.")).to_be_visible(timeout=45_000)
    expect(preview_column.get_by_text("single-file-proof", exact=False).first).to_be_visible()

    route.locator('[data-test="document-converter-mode-project"]').click()
    expect(route.get_by_text("single-file-proof", exact=False)).to_have_count(0)
    expect(route.get_by_text("Exportera som", exact=True)).to_be_visible()
    expect(preview_column.get_by_test_id("document-converter-pdf-frame")).to_be_visible()

    return {
        "compact_source_upload_before_controls": True,
        "single_file_accept": accept_value,
        "single_file_html_conversion_previewed": True,
        "single_file_mode_leak_absent_after_project_switch": True,
        "single_file_pdf_source_inferred": True,
        "single_file_remove_cleared_visible_upload": True,
    }


def _assert_compact_order(*, source_column: Locator, operations_column: Locator) -> None:
    source_box = source_column.bounding_box()
    operations_box = operations_column.bounding_box()
    if source_box is None or operations_box is None:
        raise AssertionError("Could not resolve Document Converter compact column geometry.")
    if source_box["y"] >= operations_box["y"]:
        raise AssertionError(
            "Document Converter compact file upload is not before conversion controls."
        )


def _write_html_probe(artifact_dir: Path) -> Path:
    path = artifact_dir / "single-file-proof.html"
    path.write_text(
        "<!doctype html><html lang='sv'><head><meta charset='utf-8'>"
        "<title>Single file proof</title></head>"
        "<body><h1>Single file proof</h1><p>Proof conversion body.</p></body></html>",
        encoding="utf-8",
    )
    return path


def _write_pdf_probe(artifact_dir: Path) -> Path:
    path = artifact_dir / "single-file-source.pdf"
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )
    return path
