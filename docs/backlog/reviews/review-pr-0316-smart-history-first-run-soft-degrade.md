---
type: review
id: REV-PR-0316
title: "Review: PR-0316 Smart history first-run soft-degrade"
status: approved
owners: "agents"
created: 2026-05-11
updated: 2026-05-11
reviewer: "codex"
prs:
  - PR-0316
links:
  - EPIC-27
  - ST-27-03
  - ST-27-04
  - ST-27-05
  - PR-0154
  - PR-0167
  - PR-0307
  - PR-0308
---

## TL;DR

`PR-0316` is approved. Authenticated Smart seating and grouping now soft-degrade
when `Historik` is enabled but no eligible export/share checkpoints exist:
the solver applies normally, returns `used_history=false`, and no
`blocked/no_history` response remains on the authenticated backend, OpenAPI, or
frontend contract. Public guest Smart keeps its public-only blocked response
types.

## Problem Statement

The review checks whether the first authenticated Smart run is no longer
blocked by an empty checkpoint history window, while keeping Smart-history
source boundaries strict and preserving checkpoint-backed `used_history=true`
behavior after an export/share action.

## Proposed Solution

The implementation removes the authenticated `blocked/no_history` business
result from the seating and grouping handlers, narrows the authenticated
smart-run API response models to applied-only payloads, regenerates the
frontend OpenAPI type branch, and updates frontend composables/tests so
first-run no-history responses are normal success outcomes. The new Playwright
proof creates authenticated roster/classroom assets, proves first-run
`used_history=false`, creates share-backed checkpoints, and proves a follow-up
draft reports `used_history=true`.

## Artifacts to Review

| File | Focus |
|------|-------|
| `docs/backlog/prs/pr-0316-st-27-05-smart-history-first-run-soft-degrade.md` | Scope, acceptance criteria, verification |
| `docs/backlog/stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md` | Parent story refinement |
| `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md` | Smart-history behavior statement |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_seating.py` | Seating first-run behavior and history sourcing |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_grouping.py` | Grouping first-run behavior and live-seating separation |
| `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py` | Authenticated seating response contract |
| `src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` | Authenticated grouping response contract |
| `frontend/apps/skriptoteket/src/api/openapi.d.ts` | Generated authenticated API type branch |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts` | Manual frontend smart-run type split |
| `frontend/apps/skriptoteket/src/views/apps/useSmartSeatingRun.ts` | Authenticated seating frontend handling |
| `frontend/apps/skriptoteket/src/views/apps/useSmartGroupingRun.ts` | Authenticated grouping frontend handling |
| `frontend/apps/skriptoteket/src/views/apps/usePublicSmartSeatingRun.ts` | Public guest seating blocked-response preservation |
| `frontend/apps/skriptoteket/src/views/apps/usePublicSmartGroupingRun.ts` | Public guest grouping blocked-response preservation |
| `scripts/playwright_pr_0316_smart_history_first_run_soft_degrade.py` | Live authenticated proof |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Remove authenticated `blocked/no_history` payloads | No eligible checkpoint is now normal first-run state, not a business block | [x] |
| Keep Smart-history source boundaries checkpoint-only | Draft autosave, undo/redo, historic draft rows, and public guest local state must not become history substitutes | [x] |
| Keep public guest blocked response types separate | Guest Smart remains browser-local without account-backed `Historik` | [x] |
| Require live proof for first-run and checkpoint follow-up | The user-visible contract spans auth ceremony, APIs, share checkpoint recording, and solver responses | [x] |

## Review Checklist

- [x] Scope is bounded to authenticated Smart first-run no-history behavior.
- [x] Acceptance criteria and proof obligations are reviewable.
- [x] Authenticated OpenAPI and frontend type branches no longer expose the
      stale blocked response.
- [x] Public guest Smart still has public-only blocked response types.
- [x] Empty checkpoint windows do not pull history from drafts, undo/redo, or
      public guest local state.
- [x] Eligible share-backed checkpoints still produce `used_history=true`.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-11`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions

None after the proof-hygiene follow-up.

### Passing Checks Observed

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/application/apps/classroom_planner/test_smart_grouping.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py -q`
- `pdm run fe-test -- --run useSmartSeatingRun useSmartGroupingRun classroomPlannerSmartPreferences PlannerWorkspaceShell`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run python -m scripts.playwright_pr_0316_smart_history_first_run_soft_degrade --base-url http://127.0.0.1:5173`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Changes Made

1. Recorded the retained review outcome for `PR-0316` as `approved`.
2. Resolved the proof-hygiene suggestion by deleting any stale
   `.artifacts/playwright-pr-0316-smart-history-first-run/failure.png` at
   script start before the retained browser proof begins.
