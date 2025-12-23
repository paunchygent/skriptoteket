---
type: story
id: ST-11-13
title: "Cutover + deletion + E2E"
status: done
owners: "agents"
created: 2025-12-21
updated: 2025-12-23
epic: "EPIC-11"
acceptance_criteria:
  - "Given the SPA has reached route parity, when cutover happens, then legacy templates/HTMX assets and page routes are removed and all routes are served by the SPA without redirects"
  - "Given critical flows are automated, when running Playwright E2E, then login, browse, run tool, and admin/editor paths pass against the SPA"
ui_impact: "Completes the migration and removes legacy UI code paths."
dependencies: ["ADR-0027", "ST-11-03", "ST-11-06", "ST-11-07", "ST-11-11", "ST-11-12"]
---

## Context

This is the final switch: delete legacy UI surfaces and validate with E2E before shipping.

## Completion Notes (2025-12-23)

### Deletions
- All SSR page routes (`src/skriptoteket/web/pages/*.py` - 12 files)
- All Jinja templates (`src/skriptoteket/web/templates/` - 50+ files)
- Legacy CSS (`static/css/app/`, `static/css/app.css`)
- Vendor JS (`static/vendor/htmx.min.js`, `static/vendor/codemirror/`)
- HTMX utilities (`htmx.py`, `toasts.py`, `interactive_action_forms.py`, `ui_text.py`, `vite.py`, `templating.py`)
- Orphan SSR test files (7 files)

### E2E Verification
- `playwright_st_11_21_login_modal_e2e.py` - Pass
- `playwright_ui_smoke.py` - Pass
- `playwright_st_11_07_spa_tool_run_e2e.py` - Pass (updated for SPA inline results)
- `playwright_ui_editor_smoke.py` - Pass (updated for SPA selectors)
- `playwright_st_11_18_editor_maintainers_e2e.py` - Pass

### Production Deployment
- Deployed to hemma.hule.education
- Container healthy, SPA serving all routes
- API endpoints operational
