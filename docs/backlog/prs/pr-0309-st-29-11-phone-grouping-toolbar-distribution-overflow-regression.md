---
type: pr
id: PR-0309
title: "ST-29-11: phone grouping toolbar distribution overflow regression"
status: done
owners: "agents"
created: 2026-05-09
updated: 2026-05-09
stories:
  - "ST-29-11"
tags: ["frontend", "ux", "design-system", "klassrumskartan", "toolbar", "responsive"]
dependencies:
  - "PR-0302"
  - "PR-0306"
acceptance_criteria:
  - "Given `Grupper` renders at the iPhone 15 Pro portrait review width, when the toolbar has undo/redo, new draft, randomize, reset, group-count, `Dela`, and overflow affordances available, then the toolbar does not horizontally overflow the visible action bar."
  - "Given the grouping toolbar width is too constrained for the distribution family, when the shared overflow ladder resolves hidden contributions, then the inline `Dela` affordance is hidden and the same distribution actions remain reachable through the overflow affordance."
  - "Given the group-count split control is visible on phone, when `Dela` has moved into overflow, then the decrement button, count value, and increment button all remain fully touchable inside the visible toolbar."
  - "Given phone, tablet, laptop, and desktop widths are proved, when this slice ships, then the existing `PR-0306` ordering still keeps `Dela` inline before context/reset at wider constrained widths and only moves it into overflow at phone widths that cannot fit the control family."
  - "Given authenticated and public guest grouping workspaces use the same toolbar path, when browser proof runs, then both modes keep all actions reachable without duplicated or lost share/export controls."
---

## Problem

The grouping workspace phone toolbar regressed at the iPhone 15 Pro portrait
width. The distribution family (`Dela` / export/share) is still rendered inline
when the action bar is too narrow, so the toolbar cramps and pushes the
group-count split control partly outside the visible toolbar.

This is not a new share/export behavior problem. It is an overflow ownership
regression: the distribution contribution already belongs to the shared toolbar
overflow ladder, but the phone cutover must force it into the overflow menu once
the remaining primary actions need the visible width.

## Goal

Restore deterministic phone toolbar collapse for `Grupper`:

- keep undo/redo, `Nytt utkast`, `Slumpa`, and the group-count split control
  usable in the visible row
- move the distribution family into the overflow affordance at the iPhone 15 Pro
  portrait width shown in the screenshot
- preserve the existing wider-width priority contract from `PR-0306`
- keep public guest and authenticated grouping workspaces aligned

## Non-goals

- No new share/export capability.
- No redesign of the toolbar primitive or `PlannerShareExportPanel`.
- No seating toolbar change unless the investigation proves the same phone
  regression exists there.
- No change to Smart settings, history, roster selection, or reset semantics.

## Current Evidence

- `PlannerGroupingWorkspaceToolbar.vue` declares phone thresholds and a
  contribution order of `context`, `reset`, `distribution`.
- The distribution action is marked as `data-overflow-contribution="distribution"`
  and has an overflow footer rendering path.
- The screenshot proves a phone width where the inline distribution trigger is
  still consuming space while the group-count split control is clipped.
- `PR-0306` already documents the intended distribution ownership correction, so
  this slice should repair the phone threshold/measurement seam rather than
  inventing a parallel toolbar rule.

## Recommended Solution

Keep the shared measured ladder, but tighten the grouping phone override so the
distribution contribution is hidden before it can crowd the group-count split
control. Treat the iPhone 15 Pro portrait toolbar as the regression viewport.

Implementation should prefer one of these narrow fixes:

1. Adjust the phone forced-hidden thresholds in
   `PlannerGroupingWorkspaceToolbar.vue` so `distribution` joins overflow at
   the measured width where the group-count cluster would otherwise clip.
2. If the threshold is brittle, make the grouping toolbar's forced phone logic
   account for the primary-zone minimum width of the group-count cluster before
   deciding whether distribution can remain inline.
3. Only if the root cause is shared measurement drift, patch
   `usePlannerToolbarOverflow.ts` and prove both grouping and seating toolbars.

Do not solve this with CSS clipping, hidden overflow on the action row, or a
phone-only duplicate share button. Those would hide the symptom while leaving
action reachability fragile.

## Implementation Plan

1. Reproduce the grouping toolbar at iPhone 15 Pro portrait width against the
   authenticated workspace and the public guest workspace.
2. Add or extend focused overflow tests in
   `PlannerGroupingWorkspaceToolbar.overflow.spec.ts` for the phone width where:
   - distribution is overflowed
   - group-count controls remain inline and enabled
   - overflow contains the share/export trigger
3. Patch the smallest toolbar/overflow threshold seam that makes the test pass.
4. Re-run the existing seating toolbar overflow tests to prove the shared ladder
   was not regressed.
5. Run browser proof across phone, tablet, laptop, and desktop widths. Include a
   phone screenshot that specifically proves no toolbar horizontal overflow and
   no clipped group-count control.
6. Record the exact proof artifact paths in `.codex/handoff.md`.

## Test Plan

- `pdm run fe-test -- --run PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow usePlannerToolbarOverflow`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`
- Browser proof:
  - authenticated `Grupper` at `393x852` and `390x844`
  - public guest `Grupper` at `393x852` and `390x844`
  - tablet/laptop/desktop regression widths from `scripts/playwright_pr_0302_toolbar_overflow_parity.py`

## Implementation Closeout

Implemented and verified on 2026-05-09 as a narrow grouping-toolbar phone
overflow remediation.

Key outcomes:

- Grouping phone forced overflow now keeps `context`, `reset`, and
  `distribution` as the same priority family while moving distribution into
  overflow at iPhone-class widths.
- The iPhone 15 Pro portrait proof width (`393x852`) now asserts that grouping
  hides `Dela` inline and exposes the same distribution actions through the
  overflow affordance.
- Seating keeps its existing phone ladder; the retained proof is now
  kind-specific where grouping intentionally differs for this regression.
- Focused component coverage now proves the group-count split control remains
  reachable when distribution has overflowed.

Verification:

- `pdm run fe-test -- --run PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow usePlannerToolbarOverflow`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run ruff check scripts/playwright_pr_0302_toolbar_overflow_parity.py`
- `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity --start-backend --start-vite`
  passed with artifacts under `.artifacts/playwright-pr-0302-toolbar-overflow-parity`.

## Rollback Plan

Revert the phone threshold/measurement change and any test additions. The
rollback must leave the `PR-0306` wider-width distribution ordering intact.
