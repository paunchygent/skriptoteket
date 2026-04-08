---
type: pr
id: PR-0241
title: "ST-11-25: Playwright tree normalization under scripts/playwright"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-11-25"
tags: ["frontend", "ops", "playwright", "refactor", "docs"]
dependencies:
  - "ST-11-25"
  - "REV-ST-11-25"
acceptance_criteria:
  - "Given the repo's `scripts/` root is accumulating Playwright-specific files, when this slice ships, then all existing Playwright entrypoints and shared Playwright helpers live under `scripts/playwright/` instead of the root scripts directory."
  - "Given the change should be mechanical rather than behavioral, when this slice ships, then the existing Playwright command surface still works through updated `pdm` wrappers and imports."
  - "Given browser automation has repo rules, when this slice ships, then the normalized tree still follows rule 075: one script per operational validation, shared helpers in underscored modules, and artifacts under `.artifacts/<script-name>/`."
  - "Given later performance work depends on stable placement, when this slice ships, then the repo has one clear home for future Playwright route-audit scripts without mixing them back into the root `scripts/` folder."
---

## Problem

The repo currently has many Playwright entrypoints and helpers directly in `scripts/`, which makes
the root folder noisy and weakens discoverability for future browser tooling.

Before adding a new performance-audit browser script, the repo should normalize the existing
Playwright tree so the new work lands in the right place.

## Goal

Perform a mechanical placement refactor only:

- move existing Playwright entrypoints into `scripts/playwright/`
- move existing `_playwright_*` helpers into `scripts/playwright/`
- update imports and `pdm` wrappers so the command surface remains stable

## Non-goals

- Adding the new route-performance inventory logic in this slice
- Adding LHCI or bundle-analysis dependencies in this slice
- Changing Playwright behavior or broadening coverage in this slice

## Implementation plan

1. Create `scripts/playwright/`.
2. Move existing Playwright entrypoints from `scripts/` into that child directory.
3. Move existing shared `_playwright_*` helpers into that child directory.
4. Update internal imports to the new module paths.
5. Update `pyproject.toml` `pdm` wrappers for:
   - `ui-smoke`
   - `ui-editor-smoke`
   - `ui-runtime-smoke`
   - `ui-hmr-probe`
6. Update any runbooks or docs that point at the old module paths.
7. Record the normalized tree in `.agents/handoff.md`.

## Proposed file layout

- `scripts/playwright/ui_smoke.py`
- `scripts/playwright/ui_editor_smoke.py`
- `scripts/playwright/ui_runtime_smoke.py`
- `scripts/playwright/hmr_probe.py`
- `scripts/playwright/_auth.py`
- `scripts/playwright/_browser.py`
- `scripts/playwright/_config.py`

The exact full moved set should include the currently active Playwright entrypoints/helpers, but no
new audit-specific logic yet.

## Test plan

- `pdm run docs-validate`
- run the existing canonical wrappers after the move:
  - `pdm run ui-smoke --help` or equivalent smoke-safe invocation
  - `pdm run ui-editor-smoke --help` or equivalent smoke-safe invocation
  - `pdm run ui-runtime-smoke --help` or equivalent smoke-safe invocation
  - `pdm run ui-hmr-probe --help` or equivalent smoke-safe invocation
- if any wrapper lacks a safe help path, run the narrowest import/module proof that shows the new
  module path resolves correctly

## Rollback plan

- Move the Playwright files back to the root `scripts/` directory and restore the prior wrapper
  module paths if the normalization unexpectedly breaks command resolution.

## References

- Story parent: [ST-11-25](../stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Review gate:
  [REV-ST-11-25](../reviews/review-st-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Browser automation rule:
  [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
