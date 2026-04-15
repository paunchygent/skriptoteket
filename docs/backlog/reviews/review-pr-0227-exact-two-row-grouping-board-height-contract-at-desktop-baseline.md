---
type: review
id: REV-PR-0227
title: "Review: PR-0227 exact two-row grouping board height contract at desktop baseline"
status: approved
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
reviewer: "lead-developer"
prs:
  - PR-0227
links:
  - EPIC-29
  - ST-29-11
  - PR-0226
---

## TL;DR

`PR-0227` is an approved follow-up tightening for the desktop grouping board. It narrows the
`PR-0226` height work into one exact default-state desktop proof case while keeping populated cards
safe through a persistent `234px` desktop `min-height` floor.

## Problem Statement

`PR-0226` froze a shared `480px` grouping floor, but it stopped short of freezing the exact default
two-row board math and the card floor that should persist after students are assigned. Without that
distinction, the workspace risked either open-ended ambiguity or an overly rigid hard cap that
could force clipping or internal scrolling.

## Proposed Solution

Freeze a desktop-only rule set:

- the empty/default four-card board must resolve to exactly `480px` at `1440x900`
- the underlying card rule is a persistent `234px` `min-height` floor, not a hard cap
- populated cards may grow past the floor
- smaller breakpoint workflows may diverge intentionally

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md` | Exactness contract | 5 min |
| `docs/backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md` | Story boundary | 3 min |
| `.codex/handoff.md` | Proof expectations | 2 min |

**Total estimated time:** ~10 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `PR-0227` as a bounded `ST-29-11` follow-up | This is grouping hardening, not a broader redesign | [x] |
| Limit exact `480px` proof to the empty/default desktop case | Exactness should not become a universal content cap | [x] |
| Freeze `234px` as a desktop `min-height` floor | Populated cards need room to grow beyond the default floor | [x] |
| Allow smaller breakpoints to diverge | Desktop proof math should not leak silently to lighter workflows | [x] |
| Require browser geometry proof | Class-only assertions are not enough for exact-height review | [x] |

## Review Checklist

- [x] The slice remains bounded
- [x] Empty/default exactness is separated from populated-card behavior
- [x] The `234px` rule is a `min-height` floor, not a hard cap
- [x] Smaller breakpoints are explicitly allowed to diverge
- [x] Browser-level proof is required for the exact `480px` case

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-06`
**Verdict:** `approved`

### Required Review Outputs

1. Confirm `PR-0227` stays a bounded `ST-29-11` desktop-first hardening slice rather than
   reopening the broader responsive/mobile workflow redesign.
2. Confirm the contract distinguishes the empty/default exact `480px` desktop proof case from the
   populated-card behavior after students are assigned.
3. Confirm the `234px` group-card rule is expressed as a desktop `min-height` floor, not a
   universal hard cap that would force clipping or internal scrolling for populated cards.
4. Confirm smaller breakpoints are explicitly allowed to diverge from the desktop-heavy workspace
   behavior and are not silently locked to the desktop proof math.
5. Confirm the proof plan now requires a browser-level rendered measurement for the exact `480px`
   empty/default board case in addition to class/token assertions.

### Review Resolution

The previously requested tightening is resolved. `PR-0227` now freezes a desktop-only group-card
floor where `234px` persists as the desktop `min-height` after assignment, while the exact `480px`
math is retained only for the empty/default four-card desktop proof case. The task also now states
that populated cards may grow past the floor without forced internal scrolling and that smaller
breakpoints may intentionally diverge from the desktop workspace behavior.

### Decision Approvals

- [x] `PR-0227` remains a valid bounded `ST-29-11` follow-up for desktop-first grouping hardening.
- [x] The exact `480px` rule is now correctly limited to the empty/default four-card desktop proof
      case.
- [x] The `234px` desktop card rule is now correctly frozen as a `min-height` floor that persists
      after assignment rather than as a universal maximum.
- [x] Populated cards are explicitly allowed to grow beyond the floor without mandatory internal
      scrolling in this slice.
- [x] Smaller breakpoint workflows are explicitly allowed to diverge from the desktop proof path.
- [x] The proof plan now requires rendered browser measurement for the exact empty/default
      `480px` contract.

### Reviewer Notes

- This follow-up review used to live as a supplemental section inside `REV-EPIC-29`. It is now its
  own retained review record under the target-based review workflow.

## Changes Made

1. `PR-0227` acceptance criteria now distinguish:
   - the exact empty/default desktop `480px` board proof
   - the persistent desktop `234px` card `min-height` floor after assignment
2. `PR-0227` now explicitly states that populated cards may grow beyond `234px` and must not be
   forced into clipping or mandatory internal scrolling in this slice.
3. `PR-0227` now explicitly limits the contract to the desktop proof path and allows smaller
   breakpoint workflows to diverge intentionally.
4. `PR-0227` now requires browser geometry proof via `getBoundingClientRect()` with an explicit
   `0.5px` tolerance for the empty/default `480px` verification step.
