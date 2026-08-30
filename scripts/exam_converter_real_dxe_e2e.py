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

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

_APP_PATH = "/apps/exam-converter"
_FIXTURE = Path("tests/fixtures/exam_conversion/real_inputs/1776888013-ak7-lag-och-ratt.dxe")
_FIXTURE_SHA256 = "ab39bbee54ec9004ce733e0942caa3c4934c37f87c7d35d59c9a16eca4f3839a"
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


def _review_real_result(page: Page, *, timeout_ms: int) -> tuple[int, int]:
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
    accept_all = page.locator('[data-test="exam-converter-accept-all-ai-prefill-action"]')
    expect(accept_all).to_be_enabled()
    with (
        page.expect_response(re.compile(r"/correction-session/intents(?:\?|$)")) as accept_write,
        page.expect_response(
            re.compile(r"/artifacts/answer_key_review_state_report(?:\?|$)")
        ) as accept_projection,
    ):
        accept_all.click()
    if not accept_write.value.ok or not accept_projection.value.ok:
        raise AssertionError("Bulk acceptance did not persist and reproject successfully.")
    review_remaining = page.locator('[data-test="exam-converter-result-open-questions"]')
    expect(review_remaining).to_be_visible(timeout=timeout_ms)

    review_remaining.click()
    manual_editor = page.locator('[data-test="exam-converter-manual-answer-key-editor"]')
    expect(manual_editor).to_be_visible()
    manual_gap_inputs = manual_editor.locator('input[data-test^="exam-converter-manual-gap-"]')
    gap_count = manual_gap_inputs.count()
    if gap_count < 1:
        raise AssertionError("The unchanged real DXE did not expose its manual asset-bearing item.")
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
    if not manual_write.value.ok or not manual_projection.value.ok:
        raise AssertionError("Manual answer key did not persist and reproject successfully.")
    expect(page.locator('[data-test="exam-converter-question-list-surface"]')).to_be_visible(
        timeout=timeout_ms
    )

    reviewed_rows = page.locator(
        '[data-test="exam-converter-question-list-surface"] [data-test^="exam-converter-question-row-"]'
    )
    return reviewed_rows.count(), gap_count


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
    if fixture_sha256 != _FIXTURE_SHA256:
        raise RuntimeError("The real DXE fixture bytes differ from the accepted source.")
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
        page.set_default_timeout(args.timeout_seconds * 1_000)
        try:
            login_via_auth_entry(
                page,
                base_url=config.base_url,
                email=config.email,
                password=config.password,
                next_path=_APP_PATH,
                success_heading_pattern=r"^Konvertera prov$",
                failure_artifacts_dir=artifact_dir,
                failure_screenshot_name="login-failure.png",
            )
            expect(page).to_have_url(re.compile(re.escape(_APP_PATH)))
            _upload_and_start(page, args.fixture)
            question_count, manual_gap_count = _review_real_result(
                page,
                timeout_ms=args.timeout_seconds * 1_000,
            )
            manifest.update(
                {
                    "artifacts": _download_artifacts(page, artifact_dir),
                    "authenticated_path": urlparse(page.url).path,
                    "manual_gap_count": manual_gap_count,
                    "question_count": question_count,
                    "status": "ok",
                }
            )
        except Exception as exc:
            manifest.update({"error": f"{type(exc).__name__}: {exc}", "status": "failed"})
            page.screenshot(path=str(artifact_dir / "failure.png"), full_page=True)
            raise
        finally:
            _write_manifest(manifest_path, manifest)
            context.close()
            browser.close()
    print(f"exam-converter-real-dxe-e2e: ok artifacts={artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
