---
id: "075-browser-automation"
type: "quality"
created: 2025-12-19
scope: "testing"
---

# 075: Browser Walk Proof

## Defaults (REQUIRED)

- REQUIRED: Prove UI and route behavior with an agent-driven click-through walk
  of the real application in a real browser session: the Claude built-in
  browser pane, the user's Chrome through Claude in Chrome, or the Codex
  internal browser.
- REQUIRED: Never use Playwright. Do not run, extend, or add Playwright scripts,
  do not use Playwright MCP, and do not fall back to Playwright when a browser
  session fails. Repair the browser session or report the blocker.
- REQUIRED: Never hardcode or print credentials.

## Authentication (REQUIRED)

- REQUIRED: Enter protected routes through the HuleEdu browser-session
  ceremony: `/auth/login`, the HuleEdu sign-in, then `/auth/callback`. The old
  `/login` route is a negative or recovery case only.
- REQUIRED: Never post credentials directly to the product backend, never
  inject or reuse session cookies, and never copy auth snippets from command
  history, review artifacts, or old proof scripts.
- REQUIRED: For protected shared-auth proof, Skriptoteket backend runs as the
  Docker `web` service (`skriptoteket_web`, alias `skriptoteket-web` on
  `hule-network`) so the HuleEdu Gateway `/api` proxy can reach it. Host
  Uvicorn is not a valid backend for this lane.

## Where To Walk

- Integrated proof: Hemma staging at `http://127.0.0.1:15173` through the Mac
  tunnel, signed in with the staging proof identities, per
  `docs/runbooks/run-skript-skriptoteket-staging-on-hemma-skriptoteket-staging-on-hemma.md`.
- Local iteration: the local dev stack with HuleEdu auth-integration, per
  `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md`
  (`pdm run dev-stack web-start` and `pdm run fe-dev-shared-auth`).
- Public routes can be walked directly only when the route is genuinely public
  and the proof does not claim protected-auth coverage.
- Inspect current services and occupied ports before starting a stack.

## Walk Steps (REQUIRED)

1. Open the target origin in the browser session.
2. Sign in through the HuleEdu ceremony when the route is protected.
3. Click through the changed workflow step by step the way a teacher would.
4. At each step that proves the change, capture a screenshot and read the
   accessibility tree or DOM; read console and network entries when the change
   touches requests or errors.
5. Walk the canonical desktop width and the compact workspace width that the
   change targets, and record both widths.
6. Record the origin, commit, steps, viewport widths, and evidence locations in
   `handoff.md`.

Editor checks walk the real CodeMirror editor: confirm `.cm-editor` is
visible, the "Testkör" button is present, and test mode opens before asserting
editor behavior. Close autocomplete and tooltips with Escape before reading
editor text.

## Script Bank Fixtures (REQUIRED)

If a walk depends on a tool existing (by slug), provision the tool through the
repo-level script bank. Do not create it ad hoc in the dev DB or rewrite an
existing demo tool's source code.

- Add or modify the tool in `src/skriptoteket/script_bank/bank.py` and its
  source under `src/skriptoteket/script_bank/scripts/`.
- Seed it before the walk:

```bash
pdm run seed-script-bank --slug <tool-slug>
pdm run seed-script-bank --slug <tool-slug> --sync-code
pdm run seed-script-bank --slug <tool-slug> --sync-metadata
```

Refs:

- Runbook: `docs/runbooks/runbook-script-bank-seeding.md`
- Story: `docs/backlog/stories/story-06-09-playwright-test-isolation.md`

## Existing Playwright Code

The repository still contains Playwright scripts under `scripts/`
(`playwright_*.py`, `_playwright_*.py`, `diagnose_*.py`), their `pdm run`
entries, the `playwright` dependency, and the script-surface test
`tests/unit/scripts/test_playwright_script_surface.py`. They are history, not a
proof lane: do not run them as proof and do not add new ones. Removing them
needs a governed task.
