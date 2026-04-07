---
type: review
id: REV-PR-0229
title: "Review: PR-0229 planner toolbar breakpoint overflow escalation and undo/redo shortcut parity"
status: pending
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
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

`PR-0229` is the retained review gate for the next desktop-first toolbar hardening step. The
toolbar must stay one row at the named desktop widths, collapse lower-priority controls into
overflow in an explicit order, and preserve undo/redo capability through canonical shortcuts once
those controls are no longer visibly pinned.

## Problem Statement

The current planner toolbar still hits width bands where visible actions are pushed outside the bar
before enough lower-priority controls collapse into overflow. In a desktop-first workspace, that
behavior is not acceptable, and the fallback should not be multi-row wrapping.

## Proposed Solution

Review and freeze one shared toolbar breakpoint doctrine:

- keep the toolbar one row at `1279x900`, `1366x768`, and `1440x900`
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
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.spec.ts` | Existing shared toolbar spec blind spots | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` | Current grouping/seating toolbar assertions | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` | Current guest parity assertions | 3 min |
| `frontend/apps/skriptoteket/src/components/ui/useDenseMenuSurface.ts` | Overflow-menu keyboard/focus interactions | 3 min |
| `frontend/apps/skriptoteket/src/assets/main.css` | Shared CSS-owned geometry and toolbar primitives | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts` | Shared planner layout token names | 2 min |

**Total estimated time:** ~63 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Freeze a one-row desktop toolbar rule | Multi-row fallback is not acceptable for this workspace | [ ] |
| Overflow `undo` / `redo` before `Börja om` | Undo/redo are less critical to keep visibly pinned | [ ] |
| Overflow `Börja om` before more critical controls | Required workflow, export, and context should stay visible longer | [ ] |
| Require shortcut parity for hidden undo/redo | Hidden controls must not mean lost capability | [ ] |
| Treat grouping and seating as one shared toolbar contract | Shared toolbar drift should be reviewed as one surface | [ ] |

## Review Checklist

- [ ] The toolbar breakpoint ladder is explicit for `1279x900`, `1366x768`, and `1440x900`
- [ ] The one-row desktop toolbar rule is preserved without clip, spill, or multi-row fallback
- [ ] Overflow escalation order is deliberate and matches the frozen priority contract
- [ ] `undo` / `redo` move into overflow before `Börja om`
- [ ] Shortcut behavior is reviewed together with discoverability and focus safety
- [ ] Guest and authenticated routes are evaluated as one shared toolbar contract
- [ ] The proof plan includes both focused specs and live browser checks at the named widths

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-06`
**Verdict:** `pending`

### Mandatory Repomix Package (External Review)

- Package: `.agents/repomix_packages/repomix-pr-0229-toolbar-breakpoint-overflow-review.xml`
- Template: `code-review`
- Included files: `25`

### Goal Shape To Review Against

At the named desktop-first review widths, the shared planner toolbar should behave like an explicit
priority ladder rather than a spill-prone flex row:

1. The toolbar remains one row.
2. No control is pushed outside the visible toolbar or detached at the right edge.
3. Lower-priority actions collapse into overflow before visible degradation begins.
4. `undo` / `redo` collapse into overflow before `Börja om`.
5. If width pressure grows after that, `Börja om` collapses next while more critical workflow,
   export, and context controls stay visible longer.
6. Grouping and seating follow the same shared breakpoint/overflow doctrine instead of drifting.
7. When `undo` / `redo` are no longer visibly pinned, canonical shortcuts still trigger the same
   planner actions outside editable text fields or focus-managed menu interactions.

### Required Verification

- Run:
  - `pdm run fe-test src/views/apps/components/PlannerWorkspaceActionBar.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run docs-validate`
- Manual checks:
  - authenticated `Grupper`
  - authenticated `Sittplatser`
  - guest `Grupper`
  - guest `Sittplatser`
  - `1279x900`
  - `1366x768`
  - `1440x900`
  - keyboard `undo` / `redo` outside editable text fields
  - keyboard `undo` / `redo` while focus is inside text inputs or active menu interactions

### Pass Means

- the toolbar stays one row
- no action is pushed outside the visible toolbar
- `undo` / `redo` overflow before `Börja om`
- `Börja om` overflows before more critical visible controls are displaced
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

## Changes Made

None yet. This retained review gate is pending implementation review.
