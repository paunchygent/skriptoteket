---
name: playwright-testing
description: Browser automation with Playwright for Python. Recommended for visual testing. (project)
---

# Playwright Testing

## When to Use

- Visual testing, screenshots, UI verification
- Mentions: "playwright", "screenshot", "visual test"

## Canonical Repo Rules

For Skriptoteket-specific setup (bootstrap login env vars, SPA island assets, macOS Intel vs Apple Silicon), follow:

- `.agent/rules/075-browser-automation.md`

## Repo Commands

```bash
# Existing smoke tests
pdm run ui-smoke
pdm run ui-editor-smoke
pdm run ui-runtime-smoke

# Run an ad-hoc script
pdm run python -m scripts.<module>
```

## One-Time Setup (Browsers)

Playwright needs browser binaries installed locally (per Playwright version).

```bash
# Install default browsers (Chromium + Firefox + WebKit)
pdm run playwright install

# Install a single browser
pdm run playwright install chromium

# CI/Linux: install browsers + OS deps
pdm run playwright install --with-deps

# List installed browsers
pdm run playwright install --list

# Force reinstall (useful if cache is inconsistent)
pdm run playwright install --force

# Uninstall browsers (all Playwright installs on this machine)
pdm run playwright uninstall --all
```

Playwright-managed browser cache locations:

- Windows: `%USERPROFILE%\\AppData\\Local\\ms-playwright`
- macOS: `~/Library/Caches/ms-playwright`
- Linux: `~/.cache/ms-playwright`

## macOS (Intel vs Apple Silicon)

On macOS, Playwright downloads different browser binaries depending on your architecture.

```bash
python -c "import platform; print(platform.machine())"
# Expect: arm64 (Apple Silicon) or x86_64 (Intel)
```

If you are on Apple Silicon but see Playwright looking for `mac-x64` binaries, you are likely running an x86_64
Python/terminal (Rosetta). Fix by using an arm64 Python/terminal, then reinstall browsers:

```bash
pdm run playwright uninstall --all
pdm run playwright install
```

## Troubleshooting

- Debug browser launches: `DEBUG=pw:browser pdm run ui-editor-smoke`
- Custom browser download location: set `PLAYWRIGHT_BROWSERS_PATH=/path` before `playwright install` (and when running tests).
- Use a system Node.js instead of Playwright's bundled driver: set `PLAYWRIGHT_NODEJS_PATH=/absolute/path/to/node`
- Disable automatic stale-browser cleanup: `PLAYWRIGHT_SKIP_BROWSER_GC=1`

## Quick Pattern (sync)

```python
import os

from playwright.sync_api import sync_playwright

base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
email = os.environ["BOOTSTRAP_SUPERUSER_EMAIL"]
password = os.environ["BOOTSTRAP_SUPERUSER_PASSWORD"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})

    # Login
    page.goto(f"{base_url}/login")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')  # prefer role/label locators in repo scripts
    page.wait_for_url('**/dashboard**')

    # Screenshot
    page.goto(f"{base_url}/admin/tools")
    page.screenshot(path='/tmp/admin-tools.png')
    browser.close()
```

## HTMX Caveat

Use `page.wait_for_url()` instead of waiting for navigation events.

## Context7

- Prefer `/websites/playwright_dev_python` for installation, browsers, env vars (topics: `browsers`, `ci`, `PLAYWRIGHT_BROWSERS_PATH`).
- Use `/microsoft/playwright-python` for Python API reference (sync/async APIs).
