---
type: pr
id: PR-0249
title: "ST-32-05 follow-up: singular login-first blocked state for closed public guest mode"
status: done
owners: "agents"
created: 2026-04-09
updated: 2026-04-09
stories:
  - "ST-32-05"
tags:
  [
    "frontend",
    "klassrumskartan",
    "guest-upgrade",
    "public-access",
    "copy",
    "ui-reconciliation",
  ]
dependencies:
  - "ST-32-05"
  - "ST-32-06"
  - "PR-0245"
  - "PR-0246"
acceptance_criteria:
  - "Given the current browser is marked as closed for new public Klassrumskartan authoring, when the public host renders, then it shows one blocked login-first surface instead of duplicating the same warning in both a top system message and a second panel."
  - "Given that blocked state is shown, when a teacher reads the message, then it clearly explains that Klassrumskartan has already been used signed in in that browser and therefore new classes or classrooms cannot be created there as a guest."
  - "Given the same blocked state may be reached by either the same teacher or a different person on the same machine, when the UI renders, then both `Logga in` and `Skapa konto` are offered, with `Logga in` as the primary action."
  - "Given the blocked state actions are rendered, when the teacher chooses `Logga in` or `Skapa konto`, then `Logga in` targets the canonical auth-entry route `/auth/login` and `Skapa konto` targets `/register`."
  - "Given the public host is blocked in this way, when it renders, then it does not introduce an extra permanent banner or a second repeated explanation surface elsewhere on the page."
---

## Status note

This PR is implemented locally and verified. The public Klassrumskartan host now resolves the
closed-browser guest state through one login-first blocked surface with the approved copy and
action hierarchy, instead of repeating the same message across two competing seams.

## Problem

`PR-0246` intentionally introduced a decisive login-first public blocked state for browsers that
have already crossed the one-time guest-upgrade closure boundary. The current UI tells the truth
about the blocked state, but it tells it twice across two different seams:

- the guest controller still raises the login-first closed-browser bootstrap state
- the overview view also renders a second blocked panel that reiterates the same diagnosis and
  action path

That duplication makes the blocked state feel heavier and less decisive than the policy it is
trying to express.

## Goal

Ship one narrow public-host reconciliation slice that:

- keeps the existing `PR-0246` policy unchanged
- reconciles the controller/view split into one clear blocked state
- makes `Logga in` the primary path while still offering `Skapa konto`

## Non-goals

- Changing the backend guest-upgrade or browser-closure policy
- Reopening the one-time bridge decision from `PR-0246`
- Redesigning the broader signed-out Klassrumskartan shell
- Adding a new guest onboarding banner, modal, or alternate public flow

## Recommended product copy

### Heading

- `Logga in för att fortsätta`

### Body

- `Klassrumskartan har redan använts inloggad i den här webbläsaren. Därför går det inte att skapa nya klasser eller klassrum här som gäst.`

### Actions

- Primary: `Logga in`
- Secondary: `Skapa konto`

### Optional supporting line

- `Om du inte har ett konto ännu, eller om det här är någon annans webbläsare, kan du skapa ett nytt konto.`

## Implementation plan

1. Reconcile the blocked-state contract across the real controller and view seams.
   - Keep the controller-owned login-first bootstrap truth for closed guest authoring.
   - Update the overview view so it renders that truth through exactly one blocked-state surface instead of layering a second repeated panel on top of it.
   - Remove the duplicate banner/panel split without leaving a second hidden truth-path alive.

2. Make the action path explicit and truthful.
   - Route `Logga in` to the canonical auth-entry contract at `/auth/login`.
   - Route `Skapa konto` to `/register`.
   - Keep `Logga in` visually primary and `Skapa konto` available as a secondary action.
   - Preserve the current public-host authority boundary; this remains a frontend presentation
     reconciliation only.

3. Lock the exact copy, seam ownership, and action targets in focused frontend tests.
   - Add or update controller-level proof in `src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts`.
   - Add or update view-level proof in `src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`.
   - Add or update public-host route/action proof in `src/views/PublicAppHostView.spec.ts`.

4. Re-prove the blocked public host live in the browser.

## Test plan

- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
- `pdm run fe-test -- --run src/views/PublicAppHostView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` in a
  browser marked with closed guest authoring:
  - verify only one blocked-state surface is rendered
  - verify the heading and body copy match the approved text
  - verify `Logga in` is visually primary
  - verify `Skapa konto` remains available as a secondary path
  - verify the actions point at `/auth/login` and `/register`

## Rollback plan

- Revert only the public blocked-state presentation reconciliation if the single-surface design
  proves misleading, while keeping the `PR-0246` one-time guest-closure policy intact.

## Implementation notes

- Controller/view reconciliation:
  - the guest controller still owns the closed-browser truth
  - the overview view now renders that truth through one blocked-state surface only
- Approved action path:
  - `Logga in` targets `/auth/login`
  - `Skapa konto` targets `/register`
- Error ownership:
  - stale planner/bootstrap errors are cleared when the browser is already closed for new guest
    authoring so the blocked state owns the page cleanly

## References

- Story parent:
  [ST-32-05](../stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md)
- Linked public-host consumer:
  [ST-32-06](../stories/story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)
- Zero-effect truthful UI baseline:
  [PR-0245](pr-0245-st-32-05-empty-guest-snapshot-and-zero-effect-import-ui-reconciliation.md)
- One-time guest-closure baseline:
  [PR-0246](pr-0246-st-32-05-one-time-guest-upgrade-consumption-and-repeat-import-suppression.md)
