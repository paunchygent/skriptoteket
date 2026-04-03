"""Shared Playwright browser-launch helpers for repo browser entrypoints.

This module centralizes the Chromium launch fallback used by canonical smokes
and targeted proofs. Canonical smoke entrypoints should import from here rather
than being reused as helper libraries by other browser scripts.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, Playwright
from playwright.sync_api import Error as PlaywrightError


def _find_chromium_headless_shell() -> str | None:
    """Return the newest Playwright-managed headless-shell binary when present."""

    root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not root.exists():
        return None

    candidates = sorted(root.glob("chromium_headless_shell-*"), reverse=True)
    for candidate in candidates:
        for subdir in [
            "chrome-headless-shell-mac-arm64",
            "chrome-headless-shell-mac-x64",
        ]:
            binary = candidate / subdir / "chrome-headless-shell"
            if binary.is_file():
                return str(binary)

    return None


def launch_chromium(playwright: Playwright) -> Browser:
    """Launch Chromium with the repo's headless-shell fallback on macOS."""

    try:
        return playwright.chromium.launch(headless=True)
    except PlaywrightError as exc:
        executable_path = _find_chromium_headless_shell()
        if not executable_path:
            raise

        message = str(exc)
        if "chromium_headless_shell" not in message and "Executable doesn't exist" not in message:
            raise

        print("Chromium launch failed; retrying with explicit headless shell executable_path.")
        return playwright.chromium.launch(headless=True, executable_path=executable_path)
