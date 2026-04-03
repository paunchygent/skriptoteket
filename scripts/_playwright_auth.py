"""Shared Playwright auth helpers for protected-route browser proofs.

This module holds reusable login flows so canonical UI smoke entrypoints do not
double as helper libraries for other repo browser scripts.
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, expect


def login_to_browse(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
    failure_artifacts_dir: Path | None = None,
) -> None:
    """Log in through the protected browse route and wait for the catalog shell."""

    protected_destination = f"{base_url}/browse"
    catalog_heading = page.get_by_role("heading", name=re.compile(r"^Katalog$", re.IGNORECASE))

    for attempt in range(3):
        page.goto(protected_destination, wait_until="domcontentloaded")
        if catalog_heading.count() > 0 and catalog_heading.first.is_visible():
            return

        dialog = page.get_by_role("dialog", name=re.compile(r"Logga in", re.IGNORECASE))
        if dialog.count() == 0:
            page.wait_for_timeout(750)
            continue

        expect(dialog).to_be_visible(timeout=10_000)
        dialog.get_by_label("E-post").fill(email)
        dialog.get_by_label("Lösenord").fill(password)
        dialog.get_by_role("button", name=re.compile(r"^Logga in", re.IGNORECASE)).click()

        try:
            expect(catalog_heading).to_be_visible(timeout=30_000)
            return
        except AssertionError:
            if attempt == 2 and failure_artifacts_dir is not None:
                page.screenshot(
                    path=str(failure_artifacts_dir / "login-failure.png"), full_page=True
                )
            if attempt == 2:
                raise
            page.wait_for_timeout(1_000)

    raise AssertionError("Protected-route login did not reach the catalog after three attempts.")
