# Flunk-Out Frenzy EPIC-33 Foundation Review Context

## Why you are receiving this packet

This is a follow-on offline review after the earlier architect packet and after
`REV-EPIC-33` approved the new foundation-first implementation order.

The purpose is narrower now:

- review the approved implementation sequence
- help settle the remaining pre-implementation decisions
- prevent `PR-0217` from starting with unresolved architectural ambiguity

## What is already approved

1. `PR-0214` remains the strict truth surface.
2. `PR-0215` is a bounded runtime-honesty checkpoint, not the physical-carrier
   implementation vehicle.
3. `PR-0200`, `PR-0202`, and `PR-0203` are blocked from further continuation.
4. `EPIC-33` / `ST-33-01` now sit ahead of future cut-over work.
5. The current implementation order is:
   - `PR-0220`
   - `PR-0217`
   - `PR-0218`
   - `PR-0219`

## What is intentionally still unresolved

The repo now needs explicit advice on:

1. carrier schema shape
2. exact launcher-world ownership boundary
3. donor-to-collider representation strategy
4. Rapier contact / stability policy
5. observer semantics for `PR-0219`
6. temporary correction policy
7. baseline repin trigger

## Why these are not implementation details

Each of these can materially distort the correctness of the foundation lane:

- a weak schema shape can hide role ambiguity in `PR-0217`
- a vague ownership boundary can recreate cross-world causality
- a poor collider strategy can produce fake "stable" behavior
- unbounded Rapier tuning can hide geometry/modeling mistakes
- loose observer semantics can make `PR-0219` look truthful while still
  accepting weak evidence
- temporary correction can easily become a hidden transport seam if not locked
- a sloppy repin trigger can erase the value of `PR-0214`

## Current recommendation baseline

These are our current working recommendations, which you are being asked to
validate, modify, or reject:

1. prefer one tagged `carriers[]` union over multiple role-specific arrays
2. require launcher 3D to own every causal elevated-route surface through one
   late board handoff
3. compile donor overhead assets into explicit support / guard / receiver
   colliders rather than flipping current render assets in place
4. define a narrow Rapier policy instead of tuning opportunistically
5. require raw-row-backed occupancy/progress/divergence evidence in the
   observer layer
6. allow only telemetry-visible, position-only, non-energy-increasing temporary
   correction during bring-up, with production target `0`
7. permit baseline repin only after focused proof, live trace, and manual
   launcher matrix all agree

## Most important files in this packet

- approved architecture source of truth:
  `docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`
- approved governance state:
  `docs/backlog/reviews/review-epic-33-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md`
- implementation lane:
  `docs/backlog/epics/epic-33-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md`
  `docs/backlog/stories/story-33-01-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md`
- planned slices:
  `docs/backlog/prs/pr-0217-flunk-out-frenzy-carrier-role-schema-observation-spine-contract-and-launcher-world-ownership-rules.md`
  `docs/backlog/prs/pr-0218-flunk-out-frenzy-launcher-world-carrier-compiler-and-donor-overhead-collider-foundation.md`
  `docs/backlog/prs/pr-0219-flunk-out-frenzy-physical-carrier-observer-shadow-mode-and-cutover-readiness-gate.md`
  `docs/backlog/prs/pr-0220-flunk-out-frenzy-epic-33-offline-review-packet-and-pre-implementation-decision-ask.md`

## Evidence note

The old shortcut-shaped baseline is still intentionally not normalized away.
That is the point of the current governance state.

Use the current `PR-0214` truth surface and the blocked `PR-0215` drift as
evidence that the repo is now correctly refusing to confuse "more truthful but
different" with "already ready to cut over."
