---
type: task
id: TASK-SKRIPT-11-25-01
title: 'ST-11-25: Playwright tree normalization under scripts/playwright'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-11-25
task_kind: story
acceptance_criteria:
- Given the repo's `scripts/` root is accumulating Playwright-specific files, when
  this slice ships, then all existing Playwright entrypoints and shared Playwright
  helpers live under `scripts/playwright/` instead of the root scripts directory.
- Given the change should be mechanical rather than behavioral, when this slice ships,
  then the existing Playwright command surface still works through updated `pdm` wrappers
  and imports.
- 'Given browser automation has repo rules, when this slice ships, then the normalized
  tree still follows rule 075: one script per operational validation, shared helpers
  in underscored modules, and artifacts under `.artifacts/<script-name>/`.'
- Given later performance work depends on stable placement, when this slice ships,
  then the repo has one clear home for future Playwright route-audit scripts without
  mixing them back into the root `scripts/` folder.
---

## Context

Source: `docs/backlog/prs/pr-0241-st-11-25-playwright-tree-normalization.md`. ST-11-25: Playwright tree normalization under scripts/playwright.

The repo currently has many Playwright entrypoints and helpers directly in `scripts/`, which makes the root folder noisy and weakens discoverability for future browser tooling. Before adding a new performance-audit browser script, the repo should normalize the existing Playwright tree so the new work lands in the right place. Perform a mechanical placement refactor only: - move existing Playwright entrypoints into `scripts/playwright/` - move existing `_playwright_*` helpers into `scripts/playwright/` - update imports and `pdm` wrappers so the command surface remains stable - Adding the new route-performance inventory logic in this slice - Adding LHCI or bundle-analysis dependencies in this

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-11-25-01 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

The repo currently has many Playwright entrypoints and helpers directly in `scripts/`, which makes
the root folder noisy and weakens discoverability for future browser tooling.

Before adding a new performance-audit browser script, the repo should normalize the existing
Playwright tree so the new work lands in the right place.

### Goal

Perform a mechanical placement refactor only:

- move existing Playwright entrypoints into `scripts/playwright/`
- move existing `_playwright_*` helpers into `scripts/playwright/`
- update imports and `pdm` wrappers so the command surface remains stable

### Non-goals

- Adding the new route-performance inventory logic in this slice
- Adding LHCI or bundle-analysis dependencies in this slice
- Changing Playwright behavior or broadening coverage in this slice

### Implementation plan

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
7. Record the normalized tree in `.codex/handoff.md`.

### Proposed file layout

- `scripts/playwright/ui_smoke.py`
- `scripts/playwright/ui_editor_smoke.py`
- `scripts/playwright/ui_runtime_smoke.py`
- `scripts/playwright/hmr_probe.py`
- `scripts/playwright/_auth.py`
- `scripts/playwright/_browser.py`
- `scripts/playwright/_config.py`

The exact full moved set should include the currently active Playwright entrypoints/helpers, but no
new audit-specific logic yet.

### Test plan

- `pdm run docs-validate`
- run the existing canonical wrappers after the move:
  - `pdm run ui-smoke --help` or equivalent smoke-safe invocation
  - `pdm run ui-editor-smoke --help` or equivalent smoke-safe invocation
  - `pdm run ui-runtime-smoke --help` or equivalent smoke-safe invocation
  - `pdm run ui-hmr-probe --help` or equivalent smoke-safe invocation
- if any wrapper lacks a safe help path, run the narrowest import/module proof that shows the new
  module path resolves correctly

### Rollback plan

- Move the Playwright files back to the root `scripts/` directory and restore the prior wrapper
  module paths if the normalization unexpectedly breaks command resolution.

### References

- Story parent: [ST-11-25](../stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Review gate:
  [REV-ST-11-25](../reviews/review-st-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Browser automation rule:
  [075-browser-automation](../../../.codex/rules/075-browser-automation.md)

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
