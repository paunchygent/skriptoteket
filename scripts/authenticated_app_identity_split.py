"""Authenticated app identity split proof.

Domain purpose:
    Prove the authenticated Exam Converter and Audio Transcription app
    identities open as distinct teacher-facing routes while sharing the
    existing HuleEdu auth and Sir Convert runtime machinery.

Relationships:
    - Uses the shared HuleEdu browser-session login helper.
    - Writes screenshots and a redacted manifest under
      `.artifacts/authenticated-app-identity-split/`.
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

ARTIFACT_ROOT = Path(".artifacts/authenticated-app-identity-split")
IDENTITY_PATHS = {
    "exam": "/apps/exam-converter",
    "transcript": "/apps/audio-transcription",
}
SUCCESS_HEADING_PATTERN = r"Konvertera prov|Transkribera samtal|Välj inspelning"
VIEWPORT = {"label": "desktop", "width": 1512, "height": 900}
JsonValue = str | int | float | bool | None | dict[str, "JsonValue"] | list["JsonValue"]
JsonObject = dict[str, JsonValue]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authenticated app identity split proof")
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
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


def _capture_auth_failure(page: Page, *, artifact_dir: Path, mode: str) -> None:
    page.screenshot(path=str(artifact_dir / f"auth-failure-{mode}.png"), full_page=True)
    (artifact_dir / f"auth-failure-{mode}.html").write_text(page.content(), encoding="utf-8")
    (artifact_dir / f"auth-failure-{mode}.json").write_text(
        json.dumps(
            {
                "mode": mode,
                "title": page.title(),
                "url": page.url,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _assert_url_mode(page: Page, *, mode: str) -> None:
    expect(page).to_have_url(re.compile(rf"{IDENTITY_PATHS[mode]}$"))


def _assert_exam_mode(page: Page) -> None:
    expect(page.locator('[data-test="conversion-hub-mode-exam"]')).to_have_count(0)
    expect(page.locator('[data-test="conversion-hub-mode-transcript"]')).to_have_count(0)
    expect(page.locator('[data-test="exam-converter-workflow-rail-shell"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-workspace-shell"]')).to_be_visible()
    expect(page.locator('[data-test="transcript-host-layout"]')).to_have_count(0)


def _assert_transcript_mode(page: Page) -> None:
    expect(page.locator('[data-test="conversion-hub-mode-exam"]')).to_have_count(0)
    expect(page.locator('[data-test="conversion-hub-mode-transcript"]')).to_have_count(0)
    expect(page.locator('[data-test="transcript-host-layout"]')).to_be_visible()
    expect(page.locator('[data-test="transcript-workflow-rail-shell"]')).to_be_visible()
    expect(page.locator('[data-test="transcript-workspace-shell"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-workflow-rail-shell"]')).to_have_count(0)


def _assert_mode(page: Page, *, mode: str) -> None:
    _assert_url_mode(page, mode=mode)
    if mode == "exam":
        _assert_exam_mode(page)
        return
    _assert_transcript_mode(page)


def _open_authenticated_mode(
    page: Page,
    *,
    artifact_dir: Path,
    base_url: str,
    email: str,
    mode: str,
    password: str,
) -> JsonObject:
    next_path = IDENTITY_PATHS[mode]
    try:
        login_via_auth_entry(
            page,
            base_url=base_url,
            email=email,
            password=password,
            next_path=next_path,
            success_heading_pattern=SUCCESS_HEADING_PATTERN,
            failure_artifacts_dir=artifact_dir,
            failure_screenshot_name=f"login-failure-{mode}.png",
            success_timeout_ms=45_000,
        )
    except Exception:
        _capture_auth_failure(page, artifact_dir=artifact_dir, mode=mode)
        raise
    _assert_mode(page, mode=mode)
    screenshot_path = artifact_dir / f"{mode}-mode.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    parsed = urlparse(page.url)
    return {
        "mode": mode,
        "path": parsed.path,
        "query": parsed.query,
        "screenshot": str(screenshot_path),
        "viewport": VIEWPORT,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    artifact_dir = _run_dir(Path(args.artifact_root))
    manifest: JsonObject = {
        "app": "skriptoteket",
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "command": "pdm run python -m scripts.authenticated_app_identity_split",
        "identity_paths": IDENTITY_PATHS,
        "product_identity_realm": "skriptoteket_standalone",
        "status": "running",
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        "viewport": VIEWPORT,
    }
    _write_manifest(manifest, artifact_dir)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        captures: list[JsonObject] = []
        try:
            for mode in ("exam", "transcript"):
                context = browser.new_context(
                    base_url=config.base_url,
                    viewport={"width": VIEWPORT["width"], "height": VIEWPORT["height"]},
                )
                page = context.new_page()
                page.set_default_timeout(args.timeout_seconds * 1_000)
                try:
                    captures.append(
                        _open_authenticated_mode(
                            page,
                            artifact_dir=artifact_dir,
                            base_url=config.base_url,
                            email=config.email,
                            mode=mode,
                            password=config.password,
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

    print(f"authenticated-app-identity-split: ok artifact_dir={artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
