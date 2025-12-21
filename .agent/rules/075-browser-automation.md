---
id: "075-browser-automation"
type: "quality"
created: 2025-12-19
scope: "testing"
---

# 075: Browser Automation

## Defaults (REQUIRED)

- REQUIRED: Use Playwright for new browser automation (Python).
- REQUIRED: Put scripts in `scripts/` and run them via `pdm run python -m scripts.<module>`.
- REQUIRED: Write artifacts (screenshots, traces) under `.artifacts/<script-name>/`.
- REQUIRED: Never hardcode or print credentials. Provide them via env vars or a gitignored dotenv file.
- REQUIRED: Local dev smokes use `.env` with `BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD`.
- REQUIRED: Prod smokes use a separate gitignored dotenv (e.g. `.env.prod-smoke`) with `BASE_URL` +
  `PLAYWRIGHT_EMAIL` / `PLAYWRIGHT_PASSWORD`, passed via `--dotenv` (or `DOTENV_PATH`).

## Repo Smoke Scripts

- `pdm run ui-smoke` → screenshots in `.artifacts/ui-smoke/`
- `pdm run ui-editor-smoke` → screenshots in `.artifacts/ui-editor-smoke/`
- `pdm run ui-runtime-smoke` → screenshots in `.artifacts/ui-runtime-smoke/` (apps + `/tools/<slug>/run`)

### Prod runs (recommended)

Create a gitignored `.env.prod-smoke`:

```bash
BASE_URL=https://skriptoteket.example
PLAYWRIGHT_EMAIL=...
PLAYWRIGHT_PASSWORD=...
```

Run:

```bash
pdm run ui-smoke --dotenv .env.prod-smoke
pdm run ui-editor-smoke --dotenv .env.prod-smoke
pdm run ui-runtime-smoke --dotenv .env.prod-smoke
```

Prereqs:

- Playwright installed locally: `pdm install -G dev`
- App running at `BASE_URL` (defaults to `http://127.0.0.1:8000`)
- For SPA island pages (e.g. editor), ensure the JS/CSS is available:
  - Prod-style assets: `pdm run fe-install && pdm run fe-build`, or
  - Dev/HMR: set `VITE_DEV_SERVER_URL=http://localhost:5173` and run `pdm run fe-dev`
    (keep `pdm run dev` running too).

## One-time Browser Install

Playwright needs browser binaries installed locally (per Playwright version).

```bash
# Install default browsers (Chromium + Firefox + WebKit)
pdm run playwright install

# Install specific browsers
pdm run playwright install chromium webkit firefox

# Linux/CI: install browser OS dependencies too
pdm run playwright install --with-deps

# List installed browsers (across all Playwright installs)
pdm run playwright install --list

# Force reinstall (useful if cache is inconsistent)
pdm run playwright install --force

# Uninstall browsers from all Playwright installs on this machine
pdm run playwright uninstall --all
```

Playwright-managed browser cache locations:

- Windows: `%USERPROFILE%\\AppData\\Local\\ms-playwright`
- macOS: `~/Library/Caches/ms-playwright`
- Linux: `~/.cache/ms-playwright`

To override browser download/search location, set `PLAYWRIGHT_BROWSERS_PATH=/absolute/path` for both:

- `pdm run playwright install ...`
- any script/test runs that use Playwright

## macOS (Intel vs Apple Silicon)

Playwright downloads different browser binaries depending on your architecture.

```bash
uname -m
python -c "import platform; print(platform.machine())"
# Expect: arm64 (Apple Silicon) or x86_64 (Intel)
```

If you are on Apple Silicon but see Playwright looking for `mac-x64` binaries, you are likely running an x86_64
Python/terminal (Rosetta). Fix by using an arm64 Python/terminal and reinstalling browsers:

```bash
pdm run playwright uninstall --all
rm -rf ~/Library/Caches/ms-playwright  # optional hard reset
pdm run playwright install
```

## Debugging

Useful environment variables:

- `PWDEBUG=1` (or `PWDEBUG=console`) opens Playwright Inspector and disables timeouts.
- `DEBUG=pw:browser` helps debug browser launch failures.
- `DEBUG=pw:api` enables verbose Playwright API logs.
- `PLAYWRIGHT_NODEJS_PATH=/absolute/path/to/node` uses a pre-installed Node.js for the driver.
- `PLAYWRIGHT_SKIP_BROWSER_GC=1` disables automatic stale-browser cleanup.

If you see errors like:

- `Executable doesn't exist at ...` (usually stale/partial browser install), or
- `Abort trap: 6` / `TargetClosedError` during `webkit.launch(...)`

Reset the local browser install:

```bash
pdm run playwright install --list
pdm run playwright uninstall --all
pdm run playwright install --force
```

## Script Pattern (sync)

Prefer using `scripts._playwright_config.get_config()` so scripts share the same CLI/env/dotenv behavior
(including `--dotenv`):

```python
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts._playwright_config import get_config

config = get_config()
base_url = config.base_url
email = config.email
password = config.password

artifacts_dir = Path(".artifacts/my-script")
artifacts_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.get_by_label("E-post").fill(email)
    page.get_by_label("Lösenord").fill(password)
    page.get_by_role("button", name="Logga in").click()
    expect(page.get_by_text("Inloggad som")).to_be_visible()

    page.screenshot(path=str(artifacts_dir / "home.png"), full_page=True)
    browser.close()
```

## HTMX Caveat

HTMX updates do not always trigger navigation events. Avoid relying on navigation waits (e.g. `waitForNavigation()`).
Prefer `page.wait_for_url(...)`, locator waits, or `expect(...)`.

## Context7 (Docs Refresh)

When updating these rules, pull current Playwright docs via Context7:

- `/websites/playwright_dev_python` (installation, browsers, cache paths, env vars)
- `/microsoft/playwright-python` (Python API reference)
