---
type: pr
id: PR-0224
title: "ST-29-11: desktop-first planner width stability and shrink-to-fit remediation"
status: done
owners: "agents"
created: 2026-04-05
updated: 2026-04-05
stories:
  - "ST-29-11"
tags: ["frontend", "design-system", "klassrumskartan", "planner", "desktop-first"]
dependencies:
  - "EPIC-29"
  - "PR-0195"
  - "PR-0196"
  - "PR-0197"
acceptance_criteria:
  - "Given Klassrumskartan is a desktop-first professional teacher tool, when the live authenticated planner renders in `Översikt`, `Grupper`, `Sittplatser`, or `Regler`, then the planner shell keeps one stable desktop width and does not narrow or widen per workspace mode."
  - "Given the authenticated host now wraps the planner inside a flex column route shell, when the planner root mounts there, then the root keeps a stable centered desktop width instead of shrinking to the active mode content."
  - "Given temporary guest-upgrade affordances still appear on the authenticated route, when the planner is visible, then those affordances no longer reintroduce a narrowed live planner shell."
---

## Problem

The live authenticated Klassrumskartan route had regained visible width drift
across `Översikt`, `Grupper`, `Sittplatser`, and `Regler`. The later route-shell
work made the regression much more obvious, but the real trigger was the
planner root in `ClassroomPlannerView.vue`: once mounted as a flex item, the
`mx-auto` root could shrink to the active mode content instead of keeping one
stable desktop frame.

That made the planner feel jumpy and unprofessional, and it falsely suggested
that the width problem lived only in the newer guest-upgrade wrapper.

## Goal

Land the bounded desktop-width fix only:

- keep one stable centered desktop planner shell
- remove the shrink-to-fit planner-root behavior
- preserve the full live planner width across all four planner modes
- avoid folding toolbar-priority hardening into the same close-out slice

## Non-goals

- Rewriting planner toolbar priority or overflow behavior.
- Adding mobile-first wrap fallbacks.
- Reopening guest-upgrade product behavior beyond route verification.

## What shipped

1. [frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue](../../../frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue)
   now uses `w-full max-w-[90rem] self-center` instead of `mx-auto`, so the
   planner keeps a stable centered width when mounted inside the authenticated
   flex host.
2. [frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts](../../../frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts)
   now locks that root-shell contract with a focused guard test.
3. Live browser proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
   confirmed matching stage/top-panel widths across `Översikt`, `Grupper`,
   `Sittplatser`, and `Regler`.

## Follow-up

Remaining dense-toolbar hardening is now explicitly split into
[PR-0225](pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md).
That slice owns the still-open desktop priority tiers, overflow rules, and
detached right-edge cluster prevention.

## Test plan

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts`
- Live desktop proof:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - verify `Översikt`, `Grupper`, `Sittplatser`, and `Regler` keep one stable shell width
  - verify the top panel no longer narrows per workspace mode
