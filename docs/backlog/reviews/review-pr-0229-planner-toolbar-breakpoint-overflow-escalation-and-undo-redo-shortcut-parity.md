---
type: review
id: REV-PR-0229
title: "Review: PR-0229 planner toolbar breakpoint overflow escalation and undo/redo shortcut parity"
status: approved
owners: "agents"
created: 2026-04-06
updated: 2026-04-09
reviewer: "lead-developer"
prs:
  - PR-0229
links:
  - EPIC-29
  - ST-29-03
  - ST-29-11
  - PR-0225
  - PR-0228
---

## TL;DR

`PR-0229` is the retained review gate for the desktop-first planner shell and toolbar hardening
step. Close-out proof now rests on exact live shell and overflow cutoffs, not a coarse
`1279x900`/`1366x768`/`1440x900` matrix: the authenticated shell flips cleanly at `1279px` /
`1280px`, and authenticated plus guest grouping/seating all collapse `undo/redo`, then `Börja om`,
then `Nytt utkast`, then context, then `Smart` at measured just-above / just-below thresholds.

## Problem Statement

The current planner toolbar still hits width bands where visible actions are pushed outside the bar
before enough lower-priority controls collapse into overflow. In a desktop-first workspace, that
behavior is not acceptable, and the fallback should not be multi-row wrapping.

## Proposed Solution

Review and freeze one shared shell and toolbar breakpoint doctrine:

- keep the authenticated planner shell compact through `1279px` and pin the desktop sidebar at
  `1280px`
- measure the exact live overflow thresholds for auth grouping, auth seating, guest grouping, and
  guest seating
- move `undo` / `redo` into overflow first
- move `Börja om` into overflow next if more width is needed
- keep more critical workflow, export, and context controls visible longer
- preserve undo/redo access through canonical keyboard shortcuts

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0229-st-29-11-desktop-first-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md` | Target breakpoint ladder, overflow order, and shortcut expectations | 5 min |
| `docs/backlog/prs/pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md` | Earlier toolbar hardening contract | 4 min |
| `docs/backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md` | Parent story scope | 3 min |
| `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md` | Desktop composition expectations | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue` | Shared toolbar zone ownership | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue` | Grouping toolbar priority and overflow candidates | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue` | Seating toolbar priority and overflow candidates | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue` | Shared overflow menu behavior | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue` | Export-cluster survival vs overflow decisions | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` | Shared toolbar integration path | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue` | Guest shared-shell parity path | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/usePlannerUndoRedoShortcuts.ts` | Shared auth+guest undo/redo keyboard guard seam | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.spec.ts` | Existing shared toolbar spec blind spots | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` | Current grouping/seating toolbar assertions | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.shortcuts.spec.ts` | Focused authenticated shell menu/input shortcut guard proof | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` | Current guest parity assertions | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.shortcuts.spec.ts` | Focused guest shell menu/input shortcut guard proof | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/usePlannerUndoRedoShortcuts.spec.ts` | Positive/negative shared shortcut proof | 4 min |
| `scripts/playwright_pr_0229_toolbar_overflow_threshold_check.py` | Exact live shell + overflow threshold verifier | 6 min |
| `frontend/apps/skriptoteket/src/components/ui/useDenseMenuSurface.ts` | Overflow-menu keyboard/focus interactions | 3 min |
| `frontend/apps/skriptoteket/src/assets/main.css` | Shared CSS-owned geometry and toolbar primitives | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts` | Shared planner layout token names | 2 min |

**Total estimated time:** ~85 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Freeze a one-row desktop toolbar rule | Multi-row fallback is not acceptable for this workspace | [ ] |
| Overflow `undo` / `redo` before `Börja om` | Undo/redo are less critical to keep visibly pinned | [ ] |
| Overflow `Börja om` before more critical controls | Required workflow, export, and context should stay visible longer | [ ] |
| Require shortcut parity for hidden undo/redo | Hidden controls must not mean lost capability | [ ] |
| Treat grouping and seating as one shared toolbar contract | Shared toolbar drift should be reviewed as one surface | [ ] |
| Freeze the auth shell breakpoint at `1280px` | Toolbar width cannot be reviewed honestly if the sidebar/mobile-header seam drifts | [ ] |

## Review Checklist

- [ ] The authenticated shell breakpoint is explicit at `1279px` / `1280px`
- [ ] The one-row desktop toolbar rule is preserved without clip, spill, or multi-row fallback
- [ ] Overflow escalation order is deliberate and matches the frozen priority contract
- [ ] `undo` / `redo` move into overflow before `Börja om`
- [ ] Shortcut behavior is reviewed together with discoverability and focus safety
- [ ] Guest and authenticated routes are evaluated as one shared toolbar contract
- [ ] The proof plan includes focused specs plus exact just-above / just-below live thresholds

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-08`
**Verdict:** `approved`

### Mandatory Repomix Package (External Review)

- Package: `.agents/repomix_packages/repomix-pr-0229-toolbar-breakpoint-overflow-review.xml`
- Template: `code-review`
- Included files: `25`

### Goal Shape To Review Against

At the live desktop-first cutoffs, the shared planner shell and toolbar should behave like an
explicit priority ladder rather than a spill-prone flex row:

1. The authenticated shell stays compact through `1279px` and flips to pinned desktop chrome at
   `1280px` with no double-stacked header.
2. The toolbar remains one row.
3. No control is pushed outside the visible toolbar or detached at the right edge.
4. Lower-priority actions collapse into overflow before visible degradation begins.
5. `undo` / `redo` collapse into overflow before `Börja om`.
6. If width pressure grows after that, `Börja om` collapses next while more critical workflow,
   export, and context controls stay visible longer.
7. Grouping and seating follow the same shared breakpoint/overflow doctrine instead of drifting.
8. When `undo` / `redo` are no longer visibly pinned, canonical shortcuts still trigger the same
   planner actions outside editable text fields or focus-managed menu interactions.

### Findings

- `high` — `PR-0229` claimed ownership of the post-`PR-0232` guest/auth shortcut alignment but its
  governed scope and proof still centered the authenticated shell. The real seam is shared between
  `frontend/apps/skriptoteket/src/views/apps/usePlannerUndoRedoShortcuts.ts` and
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`, so guest and
  authenticated shells must be reviewed as one contract.
- `medium` — the original proof only showed the happy path where hidden undo/redo still fire. That
  left a regression hole where a global listener could steal `Cmd/Ctrl+Z` while the teacher is
  typing or navigating overflow/menu interactions and still appear to pass.

### Required Verification

- Run:
  - `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceActionBar.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.shortcuts.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.shortcuts.spec.ts src/views/apps/usePlannerUndoRedoShortcuts.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run python -m scripts.playwright_pr_0229_toolbar_overflow_threshold_check --dotenv .env.prod-smoke`
  - `pdm run docs-validate`
- Live threshold artifacts:
  - `.artifacts/pr-0229-toolbar-overflow-thresholds/threshold-results.json`
  - `.artifacts/pr-0229-toolbar-overflow-thresholds/auth-grouping-shell-compact.png`
  - `.artifacts/pr-0229-toolbar-overflow-thresholds/auth-seating-shell-compact.png`
  - `.artifacts/pr-0229-toolbar-overflow-thresholds/*-smart-overflow.png`

### Pass Means

- the authenticated planner shell stays compact at `1279px` and flips to pinned desktop chrome at
  `1280px`
- the toolbar stays one row
- no action is pushed outside the visible toolbar
- `undo` / `redo` overflow before `Börja om`
- `Börja om` overflows before more critical visible controls are displaced
- each newly hidden contribution appears in the overflow menu at the first just-below cutoff
- shortcuts still trigger the correct planner actions when `undo` / `redo` are hidden
- shortcuts do not hijack text-entry or menu-keyboard interactions
- no route-specific divergence appears between guest and authenticated shared toolbar behavior

### Output

- Verdict: `approved` | `changes_requested` | `rejected`
- If not approved:
  - list the exact structural fault lines with file paths
  - state which breakpoint or priority assumptions were disproven
  - propose `2` to `3` fix directions with pros/cons
- If approved:
  - state the breakpoint ladder, visible/overflow order, and shortcut contract clearly enough that
    implementation can proceed without inventing missing rules

### Fix directions

1. Minimal fix: expand `PR-0229` governed scope and proof to include the guest shell plus the
   shared shortcut composable.
   - Pro: keeps the backlog slice stable.
   - Con: still relies on reviewers inferring some breakpoint and proof detail from narrative text.
2. Stronger fix: replace the coarse matrix with an exact threshold verifier that binary-searches the
   shell and overflow cutoffs, then records just-above / just-below evidence.
   - Pro: makes the breakpoint doctrine reviewable without guessing from a few named widths.
   - Con: adds one more targeted Playwright entrypoint to maintain.

## Changes Made

- Updated `PR-0229` to govern the shared shortcut seam across authenticated and guest shells,
  including `ClassroomPlannerGuestWorkspaceShell.vue`,
  `ClassroomPlannerGuestWorkspaceShell.spec.ts`, `usePlannerUndoRedoShortcuts.ts`, and
  `usePlannerUndoRedoShortcuts.spec.ts`.
- Updated `scripts/playwright_pr_0229_toolbar_overflow_threshold_check.py` so it accepts the repo's
  standard Playwright `--dotenv` contract and can run against production without ad hoc env
  wiring.
- Added focused frontend tests for the shared shortcut composable and guest-shell shortcut parity so
  re-review can check concrete auth+guest evidence instead of narrative-only claims.
- Expanded the negative-path proof so it now rests on three concrete layers rather than narrative
  claims:
  - `usePlannerUndoRedoShortcuts.spec.ts` covers the shared seam directly for editable targets,
    menu targets, already-prevented events, disabled seam state, missing draft state, and
    missing undo/redo capability.
  - `PlannerWorkspaceShell.shortcuts.spec.ts` proves the authenticated shell allows shortcuts from
    a neutral toolbar target but stays inert on a real focused menu item and a focused input
    probe.
  - `ClassroomPlannerGuestWorkspaceShell.shortcuts.spec.ts` proves the same focused menu/input
    guardrails on the guest shell without reopening the auth/guest transport seam.
- Live production threshold proof captured on 2026-04-09 against
  `https://skriptoteket.hule.education`:
  - authenticated shell cutover is exact and monotonic: compact/mobile chrome at `1279px`,
    desktop sidebar pinned at `1280px`, with `wrapperMarginLeftPx = 0` below and `240` above.
  - authenticated grouping overflow cutoffs are exact: `undo/redo` at `1237px`, `Börja om` at
    `1156px`, `Nytt utkast` at `1080px`, roster context at `991px`, and `Smart` at `568px`.
  - authenticated seating overflow cutoffs are exact: `undo/redo` at `1237px`, `Börja om` at
    `1156px`, `Nytt utkast` at `1080px`, template context at `966px`, and `Smart` at `459px`.
  - guest grouping overflow cutoffs are exact: `undo/redo` at `969px`, `Börja om` at `888px`,
    `Nytt utkast` at `812px`, roster context at `692px`, and `Smart` at `552px`.
  - guest seating overflow cutoffs are exact: `undo/redo` at `933px`, `Börja om` at `852px`,
    `Nytt utkast` at `776px`, template context at `631px`, and `Smart` at `443px`.
  - in every lane, the first just-below cutoff produced the exact next hidden-action prefix and the
    newly hidden action appeared in the overflow menu, so the proof no longer depends on a coarse
    width matrix or hidden-control inference.
- No new findings were discovered in the exact live threshold proof. The retained review remains
  `approved`: the shell breakpoint is now explicit, overflow order is measured rather than guessed,
  guest/auth parity is covered live, and the shortcut negative paths now rest on explicit shared
  seam coverage plus focused auth/guest shell integration tests.
