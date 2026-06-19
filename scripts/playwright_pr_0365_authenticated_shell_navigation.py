"""PR-0365 authenticated shell navigation browser proof.

Domain purpose:
    Prove authenticated sidebar and mobile drawer navigation stay utility-first
    after authenticated home became the owned app-entry surface and the top auth
    bar retained sole ownership of help access.

Relationships:
    - Targets `PR-0365` route-visible close-out evidence.
    - Uses the shared HuleEdu browser-session login helper rather than
      app-local cookies or protected API shortcuts.
    - Writes desktop/mobile screenshots plus a redacted manifest under
      `.artifacts/playwright-pr-0365-authenticated-shell-navigation/`.
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

from playwright.sync_api import Locator, Page, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

ARTIFACT_ROOT = Path(".artifacts/playwright-pr-0365-authenticated-shell-navigation")
STANDARD_LINKS = [
    ("Hem", "/"),
    ("Mina filer", "/vault"),
    ("Föreslå verktyg", "/suggestions/new"),
    ("Katalog", "/browse"),
    ("Profil", "/profile"),
]
ROLE_GATED_LINKS = [
    ("Mina verktyg", "/my-tools"),
    ("Hantera verktyg", "/admin/tools"),
    ("Användare", "/admin/users"),
    ("Granska förslag", "/admin/suggestions"),
]
REJECTED_NAV_COPY = [
    "Appar",
    "Plattform",
    "Vad du gör",
    "Nytta",
    "Hjälp",
    "Klassrumskartan",
    "Provhantering",
    "Ljudtranskribering",
    "Kodredigerare",
    "Mina körningar",
    "Dokumentkonvertering",
]
REJECTED_NAV_TARGETS = [
    "/apps/classroom.group-seating-studio",
    "/apps/documents.conversion_hub?mode=exam",
    "/apps/documents.conversion_hub?mode=transcript",
    "/editor",
    "/my-runs",
]
VIEWPORTS = (
    {"label": "desktop", "width": 1512, "height": 900},
    {"label": "mobile", "width": 390, "height": 844},
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PR-0365 authenticated shell navigation browser proof"
    )
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--timeout-seconds", default=90, type=int)
    return parser.parse_args(argv)


def _run_dir(root: Path) -> Path:
    path = root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_manifest(manifest: dict[str, Any], artifact_dir: Path) -> None:
    (artifact_dir / "manifest.redacted.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _visible_sidebar(page: Page) -> Locator:
    sidebar = page.locator("aside.sidebar").first
    expect(sidebar).to_be_visible()
    return sidebar


def _assert_link_sequence(nav: Locator, expected_links: list[tuple[str, str]]) -> None:
    links = nav.locator("a.sidebar-nav-item")
    expect(links.first).to_be_visible(timeout=15_000)
    link_count = links.count()
    if link_count < len(expected_links):
        raise AssertionError(
            f"Expected at least {len(expected_links)} sidebar links, found {link_count}."
        )

    for index, (label, target) in enumerate(expected_links):
        link = links.nth(index)
        expect(link).to_have_text(label)
        expect(link).to_have_attribute("href", target)


def _normalize_nav_label(text: str) -> str:
    return " ".join(text.split()).casefold()


def _assert_navigation_contract(page: Page, *, expect_open_drawer: bool) -> dict[str, Any]:
    sidebar = _visible_sidebar(page)
    if expect_open_drawer:
        class_name = sidebar.get_attribute("class") or ""
        if "is-open" not in class_name:
            raise AssertionError("Mobile sidebar drawer is visible but not marked open.")

    nav = sidebar.locator(".sidebar-nav")
    expect(nav).to_be_visible()
    nav_items = nav.locator(".sidebar-nav-item")
    expect(nav_items.first).to_be_visible(timeout=15_000)
    item_texts = [nav_items.nth(index).inner_text().strip() for index in range(nav_items.count())]
    core_item_order = [label for label, _target in STANDARD_LINKS]
    normalized_core_item_order = [_normalize_nav_label(label) for label in core_item_order]
    normalized_item_prefix = [
        _normalize_nav_label(text) for text in item_texts[: len(core_item_order)]
    ]
    if normalized_item_prefix != normalized_core_item_order:
        raise AssertionError(
            "Expected sidebar item order "
            f"{core_item_order}, found {item_texts[: len(core_item_order)]}."
        )

    present_role_links = [
        (label, target)
        for label, target in ROLE_GATED_LINKS
        if nav.get_by_role("link", name=label).count() > 0
    ]
    present_role_labels = [label for label, _target in present_role_links]
    actual_role_slice = item_texts[
        len(core_item_order) : len(core_item_order) + len(present_role_labels)
    ]
    normalized_role_labels = [_normalize_nav_label(label) for label in present_role_labels]
    normalized_actual_role_slice = [_normalize_nav_label(text) for text in actual_role_slice]
    if normalized_actual_role_slice != normalized_role_labels:
        raise AssertionError(
            "Expected role-gated links after the utility block to be "
            f"{present_role_labels}, found {actual_role_slice}."
        )

    expected_links = STANDARD_LINKS + present_role_links
    _assert_link_sequence(nav, expected_links)

    for copy in REJECTED_NAV_COPY:
        expect(nav.get_by_text(copy, exact=True)).to_have_count(0)
    for target in REJECTED_NAV_TARGETS:
        expect(nav.locator(f'a[href="{target}"]')).to_have_count(0)

    return {
        "link_order": item_texts,
        "link_targets": [target for _label, target in expected_links],
    }


def _capture_shell(
    page: Page,
    *,
    artifact_dir: Path,
    base_url: str,
    email: str,
    password: str,
    viewport: dict[str, int | str],
) -> dict[str, Any]:
    label = str(viewport["label"])
    page.set_viewport_size({"width": int(viewport["width"]), "height": int(viewport["height"])})
    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path="/",
        success_heading_pattern=r"Klassrumskartan",
        failure_artifacts_dir=artifact_dir,
        failure_screenshot_name=f"login-failure-{label}.png",
        success_timeout_ms=45_000,
    )

    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_text("Mina körningar")).to_have_count(0)
    drawer_opened = False
    if label == "mobile":
        menu_button = page.get_by_role("button", name="Meny")
        expect(menu_button).to_be_visible()
        menu_button.click()
        drawer_opened = True

    nav_contract = _assert_navigation_contract(page, expect_open_drawer=drawer_opened)
    screenshot_path = artifact_dir / f"authenticated-shell-navigation-{label}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    parsed = urlparse(page.url)
    return {
        "drawer_opened": drawer_opened,
        "label": label,
        "path": parsed.path,
        "query": parsed.query,
        "screenshot": str(screenshot_path),
        "viewport": viewport,
        **nav_contract,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = get_config(["--base-url", args.base_url, "--dotenv", args.dotenv])
    artifact_dir = _run_dir(Path(args.artifact_root))
    manifest: dict[str, Any] = {
        "app": "skriptoteket",
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "command": "pdm run python -m scripts.playwright_pr_0365_authenticated_shell_navigation",
        "product_identity_realm": "skriptoteket_standalone",
        "status": "running",
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        "viewports": VIEWPORTS,
    }
    _write_manifest(manifest, artifact_dir)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        captures: list[dict[str, Any]] = []
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
                        _capture_shell(
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

    print(f"playwright-pr-0365-authenticated-shell-navigation: ok artifact_dir={artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
