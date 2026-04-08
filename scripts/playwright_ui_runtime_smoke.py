"""Canonical Playwright smoke for the authenticated runtime execution lane.

This smoke is a canonical release gate for the runtime lane. It verifies the
shared `/auth/login` entry contract and the live curated-app runtime surfaces
that are actually shipped in the current catalog, without depending on narrower
PR-specific browser proofs.
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._playwright_flunk_out_frenzy import verify_runtime_start, wait_for_shell_ready


def _run_curated_app(page: object, *, base_url: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")
    expect(
        page.get_by_role("heading", name=re.compile(r"Interaktiv.*räknare", re.IGNORECASE))
    ).to_be_visible()
    expect(page.get_by_text(re.compile(r"Kurerad app", re.IGNORECASE))).to_be_visible()

    start_button = page.get_by_role("button", name=re.compile(r"Starta", re.IGNORECASE))
    if start_button.count() > 0 and start_button.is_visible():
        start_button.click()

    action_button = page.get_by_role("button", name=re.compile(r"Öka", re.IGNORECASE))
    if action_button.count() > 0:
        expect(action_button).to_be_visible(timeout=60_000)
    else:
        expect(
            page.get_by_text(re.compile(r"(Pågår|Lyckades|Misslyckades|Tidsgräns)", re.IGNORECASE))
        ).to_be_visible(timeout=60_000)
    page.screenshot(path=str(artifacts_dir / "curated-app.png"), full_page=True)


def _run_flunk_out_frenzy(page: object, *, base_url: str, artifacts_dir: Path) -> None:
    page.goto(f"{base_url}/apps/games.flunk_out_frenzy", wait_until="domcontentloaded")
    wait_for_shell_ready(page)
    expect(
        page.get_by_role("heading", name=re.compile(r"Flunk-Out Frenzy", re.IGNORECASE))
    ).to_be_visible()
    verify_runtime_start(page)
    page.screenshot(path=str(artifacts_dir / "flunk-out-frenzy.png"), full_page=True)


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    email = config.email
    password = config.password

    artifacts_dir = Path(".artifacts/ui-runtime-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800}, accept_downloads=True
        )
        page = context.new_page()

        login_via_auth_entry(
            page,
            base_url=base_url,
            email=email,
            password=password,
            next_path="/",
            success_heading_pattern=r"Välkommen",
            failure_artifacts_dir=artifacts_dir,
        )
        _run_curated_app(page, base_url=base_url, artifacts_dir=artifacts_dir)
        _run_flunk_out_frenzy(page, base_url=base_url, artifacts_dir=artifacts_dir)

        context.close()
        browser.close()

    print(f"Playwright artifacts written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
