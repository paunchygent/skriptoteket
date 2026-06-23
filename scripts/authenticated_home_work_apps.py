"""Authenticated home work-apps browser proof.

Domain purpose:
    Prove authenticated `/` opens the approved app-first work surface through
    the HuleEdu browser-session ceremony and Docker-backed Skriptoteket lane.

Relationships:
    - Uses the shared HuleEdu login helper instead of app-local auth shortcuts.
    - Writes desktop and compact screenshots plus a redacted manifest under
      `.artifacts/authenticated-home-work-apps/`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

ARTIFACT_ROOT = Path(".artifacts/authenticated-home-work-apps")
APP_ORDER = [
    "Klassrumskartan",
    "Provhantering",
    "Ljudtranskribering",
    "Dokumentkonvertering",
    "Kodredigerare",
]
APP_LINK_TARGETS = {
    "home-work-app-classroom": "/apps/classroom.group-seating-studio",
    "home-work-app-exam-converter": "/apps/exam-converter",
    "home-work-app-audio-transcription": "/apps/audio-transcription",
    "home-work-app-editor": "/editor",
}
REJECTED_COPY = (
    "nästa arbetsmoment",
    "nästa steg i ditt arbete",
    "filspår",
    "transkriptarbetsyta",
    "publiceringsflödet",
    "app-första startsidan",
    "nästa arbetsflöde",
    "Visas här när arbetsytan är redo",
    "Arbetsappar",
    "Direkt i appen",
    "Provkonverteraren",
    "Dokumentkonverteraren",
)
VIEWPORTS = (
    {"label": "desktop", "width": 1512, "height": 900},
    {"label": "compact", "width": 390, "height": 844},
)
JsonObject = dict[str, object]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authenticated home work-apps browser proof")
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-seconds", default=90, type=int)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    path = root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_manifest(manifest: JsonObject, artifact_dir: Path) -> None:
    (artifact_dir / "manifest.redacted.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _assert_home_contract(page: Page) -> None:
    expect(page).to_have_url(re.compile(r"/$"))
    work_apps = page.locator('[data-testid="home-work-apps"]')
    secondary_ledgers = page.locator('[data-testid="home-secondary-ledgers"]')
    home_surface = page.locator(
        '[data-testid="home-work-apps"], [data-testid="home-secondary-ledgers"]'
    )
    expect(work_apps).to_be_visible()
    expect(secondary_ledgers).to_be_visible()
    expect(work_apps.locator("h3")).to_have_text(APP_ORDER)
    expect(work_apps.locator("img")).to_have_count(5)
    expect(secondary_ledgers.get_by_text("Mina filer", exact=True)).to_be_visible()
    expect(secondary_ledgers.get_by_text("Katalog", exact=True)).to_be_visible()
    expect(work_apps.get_by_text("Exam Converter")).to_have_count(0)
    expect(work_apps.get_by_text("Audio Transcription")).to_have_count(0)
    expect(work_apps.get_by_text("Document Converter")).to_have_count(0)
    expect(work_apps.get_by_text("Kommer senare")).to_be_visible()
    for copy in REJECTED_COPY:
        expect(home_surface.get_by_text(copy)).to_have_count(0)
    expect(page.get_by_text("Mina körningar")).to_have_count(0)
    expect(page.locator('a[href="/my-runs"]')).to_have_count(0)
    expect(home_surface.get_by_text("Mina körningar")).to_have_count(0)
    expect(home_surface.get_by_text("Dina favoriter")).to_have_count(0)
    expect(home_surface.get_by_text("Senast använda")).to_have_count(0)
    expect(work_apps.get_by_text("Öppna")).to_have_count(0)

    for test_id, href in APP_LINK_TARGETS.items():
        card = page.locator(f'[data-testid="{test_id}"]')
        expect(card).to_have_attribute("data-app-linkable", "true")
        expect(card).to_have_attribute("href", href)

    document_converter = page.locator('[data-testid="home-work-app-document-converter"]')
    expect(document_converter).to_have_attribute("data-app-linkable", "false")
    expect(document_converter).not_to_have_attribute("href", re.compile(r".+"))

    work_box = work_apps.bounding_box()
    ledger_box = secondary_ledgers.bounding_box()
    if work_box is None or ledger_box is None:
        raise AssertionError("Could not resolve authenticated home section geometry.")
    if work_box["y"] >= ledger_box["y"]:
        raise AssertionError("Work app cards are not above the secondary ledgers.")


def _capture_home(
    page: Page,
    *,
    artifact_dir: Path,
    base_url: str,
    email: str,
    password: str,
    viewport: dict[str, int | str],
) -> JsonObject:
    page.set_viewport_size({"width": int(viewport["width"]), "height": int(viewport["height"])})
    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path="/",
        success_heading_pattern=r"Klassrumskartan",
        failure_artifacts_dir=artifact_dir,
        failure_screenshot_name=f"login-failure-{viewport['label']}.png",
        success_timeout_ms=45_000,
    )
    _assert_home_contract(page)
    screenshot_path = artifact_dir / f"authenticated-home-{viewport['label']}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    parsed = urlparse(page.url)
    return {
        "label": viewport["label"],
        "path": parsed.path,
        "query": parsed.query,
        "screenshot": str(screenshot_path),
        "viewport": viewport,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    artifact_dir = _run_dir(Path(args.artifact_root))
    manifest: JsonObject = {
        "app": "skriptoteket",
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "command": "pdm run python -m scripts.authenticated_home_work_apps",
        "product_identity_realm": "skriptoteket_standalone",
        "status": "running",
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        "viewports": VIEWPORTS,
    }
    _write_manifest(manifest, artifact_dir)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        captures: list[JsonObject] = []
        try:
            for viewport in VIEWPORTS:
                context = browser.new_context(
                    base_url=config.base_url,
                    viewport={"width": int(viewport["width"]), "height": int(viewport["height"])},
                )
                page = context.new_page()
                page.set_default_timeout(args.timeout_seconds * 1_000)
                try:
                    captures.append(
                        _capture_home(
                            page,
                            artifact_dir=artifact_dir,
                            base_url=config.base_url,
                            email=config.email,
                            password=config.password,
                            viewport=viewport,
                        )
                    )
                finally:
                    context.close()
            manifest["captures"] = captures
            manifest["status"] = "ok"
            _write_manifest(manifest, artifact_dir)
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = f"{type(exc).__name__}: {exc}"
            _write_manifest(manifest, artifact_dir)
            raise
        finally:
            browser.close()

    print(f"authenticated-home-work-apps: ok artifact_dir={artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
