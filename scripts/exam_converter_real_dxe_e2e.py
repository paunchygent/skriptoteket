"""Authenticated real-DXE Exam Converter end-to-end runtime path."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, expect, sync_playwright
from pydantic import JsonValue

from scripts._exam_converter_real_dxe_responsive import (
    assert_desktop_geometry,
    assert_mobile_detail,
    assert_persisted_responses,
    assert_prefill_panel,
    cancel_local_edit_and_assert_reset,
    capture_correction_request,
    selected_item_id,
)
from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

_APP_PATH = "/apps/exam-converter"
_FIXTURE = Path("tests/fixtures/exam_conversion/real_inputs/1776888013-ak7-lag-och-ratt.dxe")
_ARTIFACT_ROOT = Path(".artifacts/exam-converter-real-dxe-e2e")


def _args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authenticated Docker/Gateway real-DXE Exam Converter end-to-end path"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--fixture", type=Path, default=_FIXTURE)
    parser.add_argument("--artifact-root", type=Path, default=_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    path = root / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_manifest(path: Path, manifest: dict[str, JsonValue]) -> None:
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _upload_and_start(page: Page, fixture: Path) -> None:
    source_input = page.locator('[data-test="exam-converter-rail-source-file-input"]')
    source_input.set_input_files(str(fixture))
    expect(page.locator('[data-test="exam-converter-selected-source-file"]')).to_contain_text(
        fixture.name
    )
    start = page.locator('[data-test="exam-converter-start-conversion"]')
    expect(start).to_be_enabled()
    start.click()
    expect(page.locator('[data-test="exam-converter-running-surface"]')).to_be_visible()


def _review_real_result(page: Page, *, timeout_ms: int) -> tuple[int, int, dict[str, JsonValue]]:
    prefill = page.locator('[data-test="exam-converter-ai-prefill-panel"]')
    conversion_failed = page.get_by_text(
        "Konverteringen av provet misslyckades",
        exact=True,
    )
    review_failed = page.locator('[data-test="exam-converter-review-failed"]')
    question_list = page.locator('[data-test="exam-converter-question-list-surface"]')
    terminal = prefill.or_(question_list).or_(conversion_failed).or_(review_failed).first
    expect(terminal).to_be_visible(timeout=timeout_ms)
    if conversion_failed.is_visible():
        failure = page.locator('[data-test="exam-converter-result-strip"]').inner_text()
        raise AssertionError(f"Real DXE conversion failed: {failure}")
    if review_failed.is_visible():
        raise AssertionError(f"Real DXE review projection failed: {review_failed.inner_text()}")
    if not prefill.is_visible():
        raise AssertionError(
            "The real DXE reached the question review surface without its expected AI suggestions."
        )
    expect(prefill).to_be_visible(timeout=timeout_ms)
    responsive_evidence: dict[str, JsonValue] = {}
    correction_request_urls: list[str] = []
    page.on(
        "request",
        lambda request: capture_correction_request(request, correction_request_urls),
    )

    page.set_viewport_size({"width": 390, "height": 844})
    assert_prefill_panel(page)
    expect(page.locator(".exam-converter-question-navigator")).to_be_visible()
    expect(page.locator(".exam-converter-question-table")).not_to_be_visible()
    page.locator('[data-test="exam-converter-open-ai-prefill-action"]').click()
    detail = page.locator('[data-test="exam-converter-selected-question-detail"]')
    advisory_detail = page.locator('[data-test="exam-converter-advisory-review-detail"]')
    expect(detail).to_be_visible()
    expect(advisory_detail).to_be_visible()
    first_item_id = selected_item_id(detail)
    responsive_evidence.update(assert_mobile_detail(page, detail))
    cancel_local_edit_and_assert_reset(
        page,
        detail,
        correction_request_urls,
        first_item_id,
    )
    responsive_evidence.update(assert_desktop_geometry(page, detail))

    page.locator('[data-test="exam-converter-advisory-overview-action"]').click()
    question_list = page.locator('[data-test="exam-converter-question-list-surface"]')
    expect(question_list).to_be_visible()
    table = page.locator(".exam-converter-question-table")
    navigator = page.locator(".exam-converter-question-navigator")
    expect(table).to_be_visible()
    expect(navigator).not_to_be_visible()
    candidate_row = table.locator(f'[data-test="exam-converter-question-row-{first_item_id}"]')
    expect(candidate_row).to_be_visible()
    expect(candidate_row.get_by_role("img", name="Förslag", exact=True)).to_be_visible()
    candidate_row.click()
    expect(detail).to_be_visible()
    if selected_item_id(detail) != first_item_id:
        raise AssertionError("The selected Förslag row opened a different question.")

    individual_accept = page.locator(
        '[data-test="exam-converter-accept-advisory-answer-key-action"]'
    )
    with (
        page.expect_response(re.compile(r"/correction-session/intents(?:\?|$)")) as item_write,
        page.expect_response(
            re.compile(r"/artifacts/answer_key_review_state_report(?:\?|$)")
        ) as item_projection,
    ):
        individual_accept.click()
    assert_persisted_responses(
        item_write.value,
        item_projection.value,
        description="Individual candidate acceptance",
    )
    expect(detail.or_(question_list).first).to_be_visible(timeout=timeout_ms)
    if detail.is_visible() and selected_item_id(detail) == first_item_id:
        raise AssertionError("Individual acceptance did not advance from the resolved item.")

    if detail.is_visible():
        page.locator('[data-test="exam-converter-advisory-overview-action"]').click()
        expect(question_list).to_be_visible()
    assert_prefill_panel(page)
    accept_all = page.locator('[data-test="exam-converter-accept-all-ai-prefill-action"]')
    expect(accept_all).to_be_enabled()
    with (
        page.expect_response(re.compile(r"/correction-session/intents(?:\?|$)")) as accept_write,
        page.expect_response(
            re.compile(r"/artifacts/answer_key_review_state_report(?:\?|$)")
        ) as accept_projection,
    ):
        accept_all.click()
    assert_persisted_responses(
        accept_write.value,
        accept_projection.value,
        description="Bulk acceptance",
    )
    review_remaining = page.locator('[data-test="exam-converter-result-open-questions"]')
    expect(review_remaining).to_be_visible(timeout=timeout_ms)

    review_remaining.click()
    manual_editor = page.locator('[data-test="exam-converter-manual-answer-key-editor"]')
    expect(manual_editor).to_be_visible()
    manual_gap_inputs = manual_editor.locator('input[data-test^="exam-converter-manual-gap-"]')
    gap_count = manual_gap_inputs.count()
    if gap_count < 1:
        raise AssertionError("The real DXE did not expose its manual asset-bearing item.")
    for index in range(gap_count):
        manual_gap_inputs.nth(index).fill(f"Manuellt svar {index + 1}")
    save = page.locator('[data-test="exam-converter-apply-manual-answer-key-action"]')
    expect(save).to_be_enabled()
    with (
        page.expect_response(re.compile(r"/correction-session/intents(?:\?|$)")) as manual_write,
        page.expect_response(
            re.compile(r"/artifacts/answer_key_review_state_report(?:\?|$)")
        ) as manual_projection,
    ):
        save.click()
    assert_persisted_responses(
        manual_write.value,
        manual_projection.value,
        description="Manual answer key",
    )
    expect(page.locator('[data-test="exam-converter-question-list-surface"]')).to_be_visible(
        timeout=timeout_ms
    )

    reviewed_rows = page.locator(
        '[data-test="exam-converter-question-list-surface"] [data-test^="exam-converter-question-row-"]'
    )
    return reviewed_rows.count(), gap_count, responsive_evidence


def _download_artifacts(page: Page, artifact_dir: Path) -> dict[str, JsonValue]:
    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible()
    qti = page.locator('[data-test="exam-converter-download-file-qti_package"]')
    pdf = page.locator('[data-test="exam-converter-download-file-examnet_pdf"]')
    expect(qti).to_be_enabled()
    expect(pdf).to_be_enabled()
    with page.expect_download() as qti_download:
        qti.click()
    qti_path = artifact_dir / "qti-package.zip"
    qti_download.value.save_as(qti_path)
    with page.expect_download() as pdf_download:
        pdf.click()
    pdf_path = artifact_dir / "examnet-import.pdf"
    pdf_download.value.save_as(pdf_path)
    if not pdf_path.read_bytes().startswith(b"%PDF"):
        raise AssertionError("Downloaded Exam.net artifact is not a PDF.")
    return {
        "qti_package": {
            "sha256": hashlib.sha256(qti_path.read_bytes()).hexdigest(),
            "size_bytes": qti_path.stat().st_size,
        },
        "examnet_pdf": {
            "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
            "size_bytes": pdf_path.stat().st_size,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _args(argv)
    fixture_bytes = args.fixture.read_bytes()
    fixture_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    artifact_dir = _run_dir(args.artifact_root)
    manifest_path = artifact_dir / "manifest.redacted.json"
    manifest: dict[str, JsonValue] = {
        "base_url": config.base_url,
        "fixture": args.fixture.name,
        "fixture_sha256": fixture_sha256,
        "status": "running",
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    _write_manifest(manifest_path, manifest)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(base_url=config.base_url, accept_downloads=True)
        page = context.new_page()
        browser_errors: list[JsonValue] = []
        page.on(
            "console",
            lambda message: (
                browser_errors.append(f"console.{message.type}: {message.text}")
                if message.type == "error"
                else None
            ),
        )
        page.on("pageerror", lambda error: browser_errors.append(f"pageerror: {error}"))
        page.set_default_timeout(args.timeout_seconds * 1_000)
        try:
            login_via_auth_entry(
                page,
                base_url=config.base_url,
                email=config.email,
                password=config.password,
                next_path=_APP_PATH,
                success_heading_pattern=r"^Konvertera prov$",
                recover_to_next_path=True,
                failure_artifacts_dir=artifact_dir,
                failure_screenshot_name="login-failure.png",
            )
            expect(page).to_have_url(re.compile(re.escape(_APP_PATH)))
            _upload_and_start(page, args.fixture)
            question_count, manual_gap_count, responsive_evidence = _review_real_result(
                page,
                timeout_ms=args.timeout_seconds * 1_000,
            )
            manifest.update(
                {
                    "artifacts": _download_artifacts(page, artifact_dir),
                    "authenticated_path": urlparse(page.url).path,
                    "manual_gap_count": manual_gap_count,
                    "question_count": question_count,
                    "responsive_review": responsive_evidence,
                    "status": "ok",
                }
            )
        except Exception as exc:
            manifest.update({"error": f"{type(exc).__name__}: {exc}", "status": "failed"})
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            raise
        finally:
            manifest["browser_errors"] = browser_errors
            _write_manifest(manifest_path, manifest)
            context.close()
            browser.close()
    print(f"exam-converter-real-dxe-e2e: ok artifacts={artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
