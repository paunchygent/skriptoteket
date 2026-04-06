---
type: pr
id: PR-0227
title: "ST-29-11: exact two-row grouping board height contract at desktop baseline"
status: done
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
stories:
  - "ST-29-11"
tags: ["frontend", "klassrumskartan", "planner", "grouping", "desktop-first", "layout"]
dependencies:
  - "EPIC-29"
  - "PR-0226"
acceptance_criteria:
  - "Given a fresh grouping draft now starts with 4 groups, when the grouping board renders at the canonical desktop proof viewport (`1440x900`) in its 2-column layout and the board is still empty/default, then the full 2-row group-card block resolves to exactly `480px` tall instead of an open-ended minimum-height floor."
  - "Given the desktop 2-column grouping layout is active, when a group card renders at that breakpoint path, then each card keeps a desktop `min-height` floor of `234px` and the inter-row gap remains `12px`, with card height measured as the rendered CSS box size including padding and borders."
  - "Given the empty/default desktop 4-card board is the exactness proof case, when that board renders with no assigned students, then the contract is frozen as `234px` card floor + `12px` inter-row gap + `234px` card floor = exactly `480px` for the full two-row block."
  - "Given students are assigned into one or more desktop group cards, when content is still below the desktop floor, then the card must not shrink below `234px`; when content exceeds that floor, then the card may grow beyond `234px` without introducing clipping or mandatory internal scrolling in this slice."
  - "Given this slice is part of the desktop-first workspace overhaul, when tablet/mobile or otherwise reduced breakpoints render the grouping workflow, then they are not required to preserve this desktop exact-height contract or the full IDE-style workspace behavior."
  - "Given `PR-0226` already froze the shared grouping lane floor, when `PR-0227` lands, then it tightens only the desktop default-state group-board and card-floor contract and does not reopen guest/authenticated shell parity or broader grouping workflow behavior."
---

## Problem

`PR-0226` froze grouping around a shared `480px` desktop minimum-height floor,
but it intentionally stopped short of defining the exact row math for the
default 4-card grouping board and the desktop floor that should persist once a
card begins to fill.

The desired rule is now two-part and desktop-first:

- the empty/default 4-card board must resolve to an exact `480px` two-row block
- the desktop group-card floor behind that proof must remain a `234px`
  `min-height`, not a universal hard cap, once students are assigned

Without that distinction, the contract risks accidentally forcing clipping or
internal scrolling for populated cards, or leaking the desktop behavior into
smaller breakpoint workflows that are intentionally allowed to diverge.

## Goal

Freeze one desktop-first grouping sizing contract that is both:

- exact and reviewable for the empty/default 4-group proof case
- safe for populated cards by expressing the desktop card sizing as a
  persistent `min-height` floor rather than a universal maximum

## Non-goals

- Reopening the `PR-0226` guest/authenticated shell parity work.
- Changing the shared `480px` grouping lane floor itself.
- Locking tablet/mobile breakpoints to the same desktop board math or forcing
  smaller screens to emulate the full IDE-style workspace.
- Redesigning populated/high-content group cards into permanently scroll-bound
  containers unless a later slice explicitly approves that stronger contract.
- Changing tablet/mobile grouping layout behavior.

## Frozen decisions

1. This slice targets the default desktop 4-card board contract, not the
   entire grouping workflow.

2. The canonical proof viewport is `desktop` = `1440x900`.
   The exact-height contract must be asserted there, where the board is in its
   2-column arrangement. This slice does not freeze the same behavior for
   smaller breakpoint paths.

3. The desktop group-card floor is `234px` `min-height`.
   The contract is:
   - row 1 card floor: `234px`
   - inter-row gap: `12px`
   - row 2 card floor: `234px`

4. The empty/default desktop 4-card proof case must total exactly `480px`.
   The contract is:
   - row 1 card floor: `234px`
   - inter-row gap: `12px`
   - row 2 card floor: `234px`
   - total board block height: `480px`

5. Card height is measured as the rendered CSS box size.
   Padding and borders count toward the `234px` card contract. Shadows do not.

6. Once students are assigned at the desktop breakpoint path, a group card must
   not shrink below `234px`, but it may grow beyond that floor when content
   requires. This slice must not introduce clipping or mandatory internal
   scrolling inside populated cards.

7. Smaller breakpoint workflows may diverge intentionally from the desktop
   workspace. They are not required to preserve the desktop exact board-height
   proof or the full heavy-workspace presentation.

## Concrete sizing contract

- Desktop group-card floor in 2-row layout: `min-height: 234px`
- Desktop inter-row gap: `12px`
- Desktop empty/default 4-card board block height: exactly `480px`
- Desktop populated cards may grow above `234px`; they must not shrink below it

## Implementation plan

1. Freeze the default desktop board-row math in:
   - `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`
   - `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`
   - `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`

2. Convert the current board behavior from a pure lane-level minimum-height
   floor into:
   - a persistent desktop group-card `min-height` floor
   - an exact empty/default desktop board proof contract

3. Make the group card occupy its full desktop grid row height in the empty
   default layout rather than self-sizing only to its current content.

4. Stretch the empty drop zone/body region inside the card so the box still
   reads as intentionally full-height when the fresh draft has no assignments.

5. Preserve the existing `PR-0226` grouping floor and avoid changing guest vs
   authenticated shell behavior while tightening this card-floor math.

6. Do not force smaller breakpoints to keep the desktop exactness behavior; the
   responsive workflow may intentionally become lighter-weight outside the
   desktop path.

## Test plan

- `pdm run fe-test src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts`
- Matching assertions must prove:
  - the desktop 2-column group board exposes the explicit empty/default
    `480px` block contract
  - the desktop group-card floor is frozen as `min-height: 234px`
  - after at least one student is assigned, the desktop card still keeps the
    `234px` floor and is not hard-capped when content exceeds it
  - the exact empty/default board-height formula is asserted from rendered
    class/token contracts and not screenshot-only inference
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof on:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
  - use browser geometry (`getBoundingClientRect()`) against named board/card
    elements at `1440x900`; exactness is satisfied when the measured empty
    board height is within `0.5px` of `480px`
- Manual checklist:
  - verify a fresh grouping draft with 4 groups renders as a 2x2 board whose
    full card block measures exactly `480px` at `1440x900`
  - verify dropping one student into a group at the same desktop viewport does
    not let the card collapse below `234px`
  - verify larger populated groups can grow past `234px` without clipping or
    forced internal card scrolling
  - verify the empty/default cards still feel calm and intentional rather than
    vertically under-filled
  - verify this tightening does not regress the student-pool height or the
    shared shell parity proven by `PR-0226`
  - verify smaller breakpoints are not required to mimic the desktop-heavy
    workspace exactly

## Rollback plan

- Revert the exact row-height math if it introduces clipping or if the default
  4-card board becomes less readable than the current `PR-0226` minimum-floor
  contract.
- Fall back to the shipped `PR-0226` `480px` minimum-height floor if the exact
  empty/default desktop card-block contract proves too rigid without a separate
  internal scrolling design decision.
