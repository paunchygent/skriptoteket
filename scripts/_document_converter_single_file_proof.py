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
import re
from pathlib import Path

from playwright.sync_api import Locator, Page, Response, expect

from scripts._document_converter_proof import FORBIDDEN_ARTIFACT_MARKERS

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
    expect(route.get_by_test_id("document-converter-filename-stem")).to_have_value(
        re.compile("single-file-proof")
    )

    route.locator('[data-test="document-converter-mode-project"]').click()
    expect(route.get_by_text("single-file-proof", exact=False)).to_have_count(0)
    expect(route.get_by_text("Exportera som", exact=True)).to_be_visible()
    expect(preview_column.get_by_test_id("document-converter-pdf-frame")).to_be_visible()
    saved_batch = _assert_saved_file_batch(page=page, route=route, artifact_dir=artifact_dir)

    return {
        "compact_source_upload_before_controls": True,
        "saved_file_batch": saved_batch,
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


def _assert_saved_file_batch(*, page: Page, route: Locator, artifact_dir: Path) -> JsonObject:
    first_name = _seed_saved_pdf_source(
        page=page,
        route=route,
        artifact_dir=artifact_dir,
        slug="pr-0404-source-a",
        heading="PR-0404 saved source A",
    )
    second_name = _seed_saved_pdf_source(
        page=page,
        route=route,
        artifact_dir=artifact_dir,
        slug="pr-0404-source-b",
        heading="PR-0404 saved source B",
    )

    route.locator('[data-test="document-converter-origin-saved"]').click()
    saved_select = route.get_by_test_id("document-converter-saved-file-select")
    expect(saved_select).to_be_visible(timeout=15_000)
    first_ref = _select_saved_file(saved_select=saved_select, label=first_name)
    second_ref = _select_saved_file(saved_select=saved_select, label=second_name)

    source_column = route.get_by_test_id("document-converter-source-column")
    first_row = source_column.locator(".dc-source-row").filter(has_text=first_name)
    second_row = source_column.locator(".dc-source-row").filter(has_text=second_name)
    expect(first_row).to_be_visible()
    expect(second_row).to_be_visible()
    expect(route).not_to_contain_text("vault:")

    route.get_by_test_id("document-converter-source-move-up-1").click()
    _assert_visible_saved_order(source_column=source_column, first=second_name, second=first_name)

    route.locator('[data-test="document-converter-output-md"]').click()
    request_payload: dict[str, object] = {}
    with page.expect_request(
        lambda request: (
            "/api/v1/apps/documents.conversion_hub/document-converter/saved-files/jobs"
            in request.url
            and request.method == "POST"
        ),
        timeout=45_000,
    ) as submit_request_info:
        with page.expect_response(
            lambda response: (
                "/api/v1/apps/documents.conversion_hub/document-converter/saved-files/jobs"
                in response.url
                and response.request.method == "POST"
            ),
            timeout=45_000,
        ) as submit_response_info:
            route.get_by_test_id("document-converter-start-single-file").click()
    submit_request = submit_request_info.value
    if submit_request.post_data:
        request_payload = json.loads(submit_request.post_data)
    submit_response = submit_response_info.value
    if submit_response.status != 200:
        _write_failed_response(
            path=artifact_dir / "document-converter-saved-file-batch-submit-response.json",
            response=submit_response,
        )
        raise AssertionError(
            f"Document Converter saved-file batch submit failed with {submit_response.status}."
        )
    if request_payload.get("source_refs") != [second_ref, first_ref]:
        raise AssertionError(
            "Saved-file batch did not submit refs in visible order: "
            f"{request_payload.get('source_refs')!r}."
        )
    if "source_ref" in request_payload or "files" in request_payload:
        raise AssertionError(
            f"Saved-file batch submitted retired or byte payload: {request_payload!r}."
        )

    operations_column = route.get_by_test_id("document-converter-operations-column")
    expect(
        operations_column.get_by_text("Markdown klart att ladda ned eller spara.")
    ).to_be_visible(timeout=60_000)
    artifact_selector = route.get_by_test_id("document-converter-artifact-selector")
    expect(artifact_selector).to_be_visible(timeout=15_000)
    artifact_labels = artifact_selector.locator(
        ".dc-artifact-selector__item span"
    ).all_inner_texts()
    if len(artifact_labels) != 2:
        raise AssertionError(f"Expected two saved-file batch outputs, got {artifact_labels!r}.")

    download_path = _download_current_result(page=page, route=route, artifact_dir=artifact_dir)
    downloaded_text = download_path.read_text(encoding="utf-8", errors="replace")
    marker_hits = [marker for marker in FORBIDDEN_ARTIFACT_MARKERS if marker in downloaded_text]
    if marker_hits:
        raise AssertionError(
            f"Saved-file batch download contained forbidden markers: {marker_hits!r}."
        )

    with page.expect_response(
        lambda response: (
            "/api/v1/apps/documents.conversion_hub/document-converter/jobs/" in response.url
            and "/artifact/save" in response.url
            and response.request.method == "POST"
        ),
        timeout=45_000,
    ) as save_response_info:
        route.get_by_test_id("document-converter-save").click()
    save_response = save_response_info.value
    if save_response.status != 200:
        _write_failed_response(
            path=artifact_dir / "document-converter-saved-file-batch-save-response.json",
            response=save_response,
        )
        raise AssertionError(
            f"Document Converter saved-file batch result save failed with {save_response.status}."
        )

    _assert_forbidden_ui_language_absent(route=route)
    return {
        "downloaded_artifact": str(download_path),
        "downloaded_artifact_bytes": download_path.stat().st_size,
        "forbidden_marker_hits": marker_hits,
        "saved_batch_output_count": len(artifact_labels),
        "saved_batch_output_labels": artifact_labels,
        "saved_batch_request_refs_only": True,
        "saved_batch_saved_source_order": [second_name, first_name],
        "saved_result_status": save_response.status,
        "seeded_saved_source_names": [first_name, second_name],
    }


def _seed_saved_pdf_source(
    *,
    page: Page,
    route: Locator,
    artifact_dir: Path,
    slug: str,
    heading: str,
) -> str:
    route.locator('[data-test="document-converter-mode-single"]').click()
    route.locator('[data-test="document-converter-origin-upload"]').click()
    html_path = _write_batch_seed_html(artifact_dir=artifact_dir, slug=slug, heading=heading)
    route.get_by_test_id("document-converter-single-file-input").set_input_files(str(html_path))
    route.locator('[data-test="document-converter-output-pdf"]').click()

    with page.expect_response(
        lambda response: (
            "/api/v1/apps/documents.conversion_hub/document-converter/jobs" in response.url
            and "/saved-files/" not in response.url
            and response.request.method == "POST"
        ),
        timeout=45_000,
    ) as submit_response_info:
        route.get_by_test_id("document-converter-start-single-file").click()
    submit_response = submit_response_info.value
    if submit_response.status != 200:
        _write_failed_response(
            path=artifact_dir / f"{slug}-submit-response.json",
            response=submit_response,
        )
        raise AssertionError(f"Seed conversion {slug} failed with {submit_response.status}.")

    expect(route.get_by_test_id("document-converter-preview-column-title")).to_have_text("Resultat")
    expect(route.get_by_test_id("document-converter-filename-stem")).to_have_value(
        re.compile(slug),
        timeout=60_000,
    )
    expect(route.get_by_test_id("document-converter-operations-column")).to_contain_text(".pdf")
    route.get_by_test_id("document-converter-filename-stem").fill(slug)
    with page.expect_response(
        lambda response: (
            "/api/v1/apps/documents.conversion_hub/document-converter/jobs/" in response.url
            and "/artifact/save" in response.url
            and response.request.method == "POST"
        ),
        timeout=45_000,
    ) as save_response_info:
        route.get_by_test_id("document-converter-save").click()
    save_response = save_response_info.value
    if save_response.status != 200:
        _write_failed_response(
            path=artifact_dir / f"{slug}-save-response.json",
            response=save_response,
        )
        raise AssertionError(f"Seed save {slug} failed with {save_response.status}.")
    payload = save_response.json()
    saved_name = payload.get("vault_artifact", {}).get("name")
    if not isinstance(saved_name, str) or not saved_name.endswith(".pdf"):
        raise AssertionError(f"Seed save {slug} returned unexpected payload: {payload!r}.")
    route.locator('[data-test="document-converter-origin-saved"]').click()
    expect(route.get_by_test_id("document-converter-saved-file-select")).to_contain_text(
        saved_name,
        timeout=20_000,
    )
    return saved_name


def _write_batch_seed_html(*, artifact_dir: Path, slug: str, heading: str) -> Path:
    path = artifact_dir / f"{slug}.html"
    path.write_text(
        "<!doctype html><html lang='sv'><head><meta charset='utf-8'>"
        f"<title>{heading}</title></head><body>"
        f"<h1>{heading}</h1>"
        f"<p>{slug} proves saved-file batch source selection.</p>"
        "</body></html>",
        encoding="utf-8",
    )
    return path


def _select_saved_file(*, saved_select: Locator, label: str) -> str:
    ref_value = saved_select.evaluate(
        """(select, label) => {
            const option = Array.from(select.options).find((item) => item.textContent.trim() === label);
            if (!option) return null;
            return option.value;
        }""",
        label,
    )
    if not isinstance(ref_value, str) or not ref_value.startswith("vault:"):
        raise AssertionError(f"Could not find saved source option {label!r}.")
    saved_select.select_option(value=ref_value)
    return ref_value


def _assert_visible_saved_order(*, source_column: Locator, first: str, second: str) -> None:
    labels = source_column.locator(".dc-source-row strong").all_inner_texts()
    if len(labels) < 2 or first not in labels[0] or second not in labels[1]:
        raise AssertionError(f"Unexpected visible saved-file order: {labels!r}.")


def _download_current_result(*, page: Page, route: Locator, artifact_dir: Path) -> Path:
    with page.expect_download(timeout=45_000) as download_info:
        route.get_by_test_id("document-converter-download").click()
    download = download_info.value
    suggested = download.suggested_filename or "saved-file-batch-result.md"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", suggested).strip("-") or "result.md"
    path = artifact_dir / f"saved-file-batch-{safe_name}"
    download.save_as(str(path))
    return path


def _write_failed_response(*, path: Path, response: Response) -> None:
    body: str
    try:
        body = response.text()
    except Exception as exc:  # pragma: no cover - live-proof fallback
        body = f"<unavailable: {type(exc).__name__}: {exc}>"
    path.write_text(
        json.dumps(
            {
                "body": body,
                "headers": dict(response.headers),
                "status": response.status,
                "url": response.url,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _assert_forbidden_ui_language_absent(*, route: Locator) -> None:
    visible_text = route.inner_text()
    forbidden_terms = (
        "artifact",
        "document-converter:",
        "job_",
        "producer",
        "source_ref",
        "source_refs",
        "vault:",
        "återställ arbetsyta",
        "historik",
    )
    hits = [term for term in forbidden_terms if term in visible_text]
    if hits:
        raise AssertionError(f"Document Converter saved-file batch leaked UI terms: {hits!r}.")


def _write_pdf_probe(artifact_dir: Path) -> Path:
    path = artifact_dir / "single-file-source.pdf"
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )
    return path
