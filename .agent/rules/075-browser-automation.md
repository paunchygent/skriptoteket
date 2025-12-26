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
- REQUIRED: If a test needs a specific “demo tool/script”, do **not** create it ad hoc in the dev DB or rewrite an
  existing demo tool’s source code. Add a dedicated entry to the **repo script bank** (`src/skriptoteket/script_bank/`)
  and seed it to the DB before running Playwright (see “Script bank fixtures” below).

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
- Backend API running (dev): `pdm run dev` (default: `http://127.0.0.1:8000`)
- `BASE_URL` should point at the **frontend** you want to test:
  - Dev/HMR: `http://127.0.0.1:5173` with `pdm run fe-dev` (Vite proxies `/api/*` to `:8000`)
  - Prod-style: your deployed host, or `http://127.0.0.1:8000` after `pdm run fe-install && pdm run fe-build`
    (backend serves built SPA)

## Script bank fixtures (REQUIRED)

If a Playwright script depends on a tool existing (by slug), the tool must be provisioned via the repo-level script bank:

- Add/modify the tool in `src/skriptoteket/script_bank/bank.py` and its source under
  `src/skriptoteket/script_bank/scripts/`.
- Seed locally before running Playwright:

```bash
# Ensure the tool exists (and optionally sync code/metadata if it already exists)
pdm run seed-script-bank --slug <tool-slug>
pdm run seed-script-bank --slug <tool-slug> --sync-code
pdm run seed-script-bank --slug <tool-slug> --sync-metadata
```

Rationale: avoids demo-script proliferation and prevents Playwright from polluting the dev DB by creating/re-writing
tools on the fly (see ST-06-09).

Refs:

- Runbook: `docs/runbooks/runbook-script-bank-seeding.md`
- Story: `docs/backlog/stories/story-06-09-playwright-test-isolation.md`

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

If you're running Playwright under a sandboxed agent environment (e.g. Codex CLI), browser launch may require
explicit approval/escalation in that environment.

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

## CodeMirror (CM6) interaction patterns (REQUIRED)

- REQUIRED: Scope editor interactions to `.cm-editor .cm-content` (avoid broad `page.get_by_text(...)` that can match
  autocomplete/tooltips instead of the editor).
- REQUIRED: For “set the whole document”, prefer `.cm-content.fill(source)` after focusing the editor; for incremental
  edits, use `page.keyboard.type(...)` after focus.
- REQUIRED: Always close autocomplete/tooltips before asserting hover or editor text (`page.keyboard.press("Escape")`),
  otherwise locators can hit `.cm-tooltip-autocomplete` instead of editor content.
- REQUIRED: Hover tooltips are DOM-fragile; prefer coordinate-based hovering over a DOM Range inside `.cm-content` (see
  `_hover_codemirror_text(...)` in `scripts/playwright_st_08_10_script_editor_intelligence_e2e.py`).
- REQUIRED: Autocomplete assertions should target `.cm-tooltip-autocomplete` presence + content; avoid exact `<li>` text
  matching (rendered labels/details can vary).
- REQUIRED: Lint assertions should click `.cm-lint-marker` and assert `.cm-tooltip-lint` contains the Swedish message
  snippet; close with Escape.
- REQUIRED: Lint updates are debounced and can lag after `.cm-content.fill(...)`; poll for the expected tooltip text
  instead of assuming the first marker is the new diagnostic (see `_expect_any_lint_message(...)` in
  `scripts/playwright_st_08_11_script_editor_intelligence_phase2_e2e.py`).
- REQUIRED: If editor intelligence is dynamically loaded, the E2E must first wait for a deterministic signal that
  extensions are active (e.g., a lint marker appears after typing invalid code) before asserting completions/hover.

References:

- Canonical CodeMirror E2E patterns: `scripts/playwright_st_08_10_script_editor_intelligence_e2e.py`
- Canonical CodeMirror lint polling patterns: `scripts/playwright_st_08_11_script_editor_intelligence_phase2_e2e.py`
- Canonical “set editor content” helper style: `scripts/playwright_st_12_02_native_pdf_output_helper_e2e.py`

## Navigation Caveat

SPA route changes (and any legacy HTMX-style flows) do not always trigger full navigation events.
Prefer `page.wait_for_url(...)`, locator waits, or `expect(...)` over navigation waits.

## Context7 (Docs Refresh)

When updating these rules, pull current Playwright docs via Context7:

- `/websites/playwright_dev_python` (installation, browsers, cache paths, env vars)
- `/microsoft/playwright-python` (Python API reference)
