"""PR-0356 live proof for authenticated Exam Converter source-only fixture UI.

Domain purpose:
    Capture authenticated live browser evidence for the governed Exam Converter
    fixture lane after the source-only intake cleanup.

Relationships:
    - Targets `PR-0356` / `ST-21-10` live UI proof requirements.
    - Uses the shared HuleEdu browser-session login helper.
    - Writes redacted screenshots and a manifest under
      `.artifacts/playwright-pr-0356-source-only-fixture-proof/`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0356-source-only-fixture-proof")
APP_HEADING_PATTERN = r"^Konvertera prov$"
FIXTURE_PATHS = {
    "complete-qti-ready": "/apps/documents.conversion_hub/exam-converter/ui-fixtures/complete-qti-ready",
    "missing-facit": "/apps/documents.conversion_hub/exam-converter/ui-fixtures/missing-facit",
}
VIEWPORTS = (
    {"label": "desktop", "width": 1512, "height": 900},
    {"label": "compact", "width": 1024, "height": 768},
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PR-0356 authenticated Exam Converter source-only fixture proof"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-seconds", default=60, type=int)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / timestamp
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_manifest(manifest: dict[str, Any], artifact_dir: Path) -> None:
    (artifact_dir / "manifest.redacted.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _expect_source_only_rail(page: Page) -> None:
    expect(page.locator('[data-test="exam-converter-workflow-rail-shell"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-supporting-file-input"]')).to_have_count(0)
    expect(page.locator('[data-test="exam-converter-target-pdf"]')).to_have_count(0)
    expect(page.locator('[data-test="exam-converter-target-qti"]')).to_have_count(0)
    expect(page.get_by_text("Valfritt rättat prov")).to_have_count(0)
    expect(page.get_by_text("QTI-format")).to_have_count(0)


def _open_fixture(
    page: Page,
    *,
    artifact_dir: Path,
    base_url: str,
    email: str,
    password: str,
    next_path: str,
    screenshot_name: str,
) -> str:
    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path=next_path,
        success_heading_pattern=APP_HEADING_PATTERN,
        failure_artifacts_dir=artifact_dir,
        failure_screenshot_name=screenshot_name,
    )
    expect(page).to_have_url(re.compile(re.escape(next_path)))
    expect(page.locator('main[aria-labelledby="exam-converter-auth-title"]')).to_be_visible()
    return urlparse(page.url).path


def _capture_complete_qti_ready(
    page: Page, *, artifact_dir: Path, viewport: dict[str, Any]
) -> dict[str, Any]:
    page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
    expect(page.locator('[data-inspection-fixture-id="complete-qti-ready"]')).to_be_visible()
    _expect_source_only_rail(page)
    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-download-file-examnet_pdf"]')).to_be_enabled()
    expect(page.locator('[data-test="exam-converter-download-file-qti_package"]')).to_be_enabled()
    expect(page.locator('[data-test="exam-converter-save-file-examnet_pdf"]')).to_be_enabled()
    expect(page.locator('[data-test="exam-converter-save-file-qti_package"]')).to_be_enabled()
    screenshot_path = artifact_dir / f"complete-qti-ready-{viewport['label']}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    return {
        "fixture": "complete-qti-ready",
        "inspection_tab": "files",
        "path": urlparse(page.url).path,
        "screenshot": str(screenshot_path),
        "viewport": viewport,
    }


def _capture_missing_facit(
    page: Page, *, artifact_dir: Path, viewport: dict[str, Any]
) -> dict[str, Any]:
    page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
    expect(page.locator('[data-inspection-fixture-id="missing-facit"]')).to_be_visible()
    _expect_source_only_rail(page)
    expect(page.locator('[data-test="exam-converter-question-review-shell"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-inspection-tab-questions"]')).to_have_attribute(
        "aria-selected",
        "true",
    )
    expect(page.locator('[data-test="exam-converter-question-row-item-001"]')).to_contain_text(
        "Vilket påstående beskriver DNA bäst?"
    )
    screenshot_path = artifact_dir / f"missing-facit-{viewport['label']}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    return {
        "fixture": "missing-facit",
        "inspection_tab": "questions",
        "path": urlparse(page.url).path,
        "screenshot": str(screenshot_path),
        "viewport": viewport,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    artifact_dir = _run_dir(Path(args.artifact_root))
    manifest: dict[str, Any] = {
        "app": "skriptoteket",
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "command": "pdm run python -m scripts.playwright_pr_0356_source_only_fixture_proof",
        "product_identity_realm": "skriptoteket_standalone",
        "status": "running",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "viewports": VIEWPORTS,
    }
    _write_manifest(manifest, artifact_dir)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            base_url=config.base_url,
            viewport={"width": VIEWPORTS[0]["width"], "height": VIEWPORTS[0]["height"]},
        )
        page = context.new_page()
        page.set_default_timeout(args.timeout_seconds * 1_000)
        try:
            desktop_path = _open_fixture(
                page,
                artifact_dir=artifact_dir,
                base_url=config.base_url,
                email=config.email,
                password=config.password,
                next_path=FIXTURE_PATHS["complete-qti-ready"],
                screenshot_name="login-failure-complete-qti-ready.png",
            )
            manifest["auth_entry"] = {
                "fixture_path": desktop_path,
            }
            captures: list[dict[str, Any]] = []
            for viewport in VIEWPORTS:
                page.goto(FIXTURE_PATHS["complete-qti-ready"], wait_until="domcontentloaded")
                captures.append(
                    _capture_complete_qti_ready(page, artifact_dir=artifact_dir, viewport=viewport)
                )
            for viewport in VIEWPORTS:
                page.goto(FIXTURE_PATHS["missing-facit"], wait_until="domcontentloaded")
                captures.append(
                    _capture_missing_facit(page, artifact_dir=artifact_dir, viewport=viewport)
                )
            manifest["captures"] = captures
            manifest["status"] = "ok"
            _write_manifest(manifest, artifact_dir)
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = f"{type(exc).__name__}: {exc}"
            _write_manifest(manifest, artifact_dir)
            raise
        finally:
            context.close()
            browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
