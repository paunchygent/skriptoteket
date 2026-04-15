# Flunk-Out Frenzy EPIC-33 Foundation Review Brief

## Role

You are the offline reviewer and planning advisor for the approved
`EPIC-33` foundation lane that now precedes any further physical cut-over work
for the Flunk-Out Frenzy launcher corridor.

## Purpose

We have already:

1. audited the shortcut and truth-gate failures (`PR-0212`)
2. made the trace surface truthful and operational (`PR-0213`, `PR-0214`)
3. exposed real drift when shortcut energy was reduced (`PR-0215`)
4. obtained and canonized one architect direction
5. approved a new foundation-first lane (`EPIC-33`, `ST-33-01`,
   `PR-0217` / `PR-0218` / `PR-0219`)

What we need from you now is not a blank-slate architecture pitch. We need a
decision-grade review of the new implementation order and explicit advice on
the critical uncertainties that still must be settled before `PR-0217`
implementation begins.

This brief accompanies:

- planning task:
  `docs/backlog/prs/pr-0220-flunk-out-frenzy-epic-33-offline-review-packet-and-pre-implementation-decision-ask.md`
- review package:
  `.agents/repomix_packages/repomix-flunk-out-frenzy-epic-33-foundation-review.xml`

## Current approved implementation order

1. `PR-0220` asks for this review and decision guidance.
2. `PR-0217` should define carrier-role schema, observation-spine semantics,
   and launcher-world ownership rules.
3. `PR-0218` should compile donor-backed launcher-world carrier colliders.
4. `PR-0219` should add observer shadow mode and cut-over readiness gating.
5. Only after `ST-33-01` is complete may blocked cut-over work resume.

Please review that order and tell us if it is correct or if it should change.

## What has already been settled

The current docs-as-code state already settles these points:

- `travelRoutes` should not remain motion-owning cut-over primitives
- the physical carrier foundation must land before cut-over continuation
- `PR-0214` remains strict during migration
- `PR-0215` is a bounded runtime-honesty checkpoint, not the physical-carrier
  implementation vehicle
- `PR-0200`, `PR-0202`, and `PR-0203` are blocked behind `ST-33-01`

Please do not spend your time re-deciding those unless you believe the approved
docs are wrong.

## Critical uncertainties still to settle

These are the real pre-cut-over questions still open.

### 1. Carrier schema shape in `PR-0217`

We still need to pin whether the model should be:

- one tagged `carriers[]` union, or
- multiple role-specific arrays

Current recommendation: prefer the tagged union because receivers and seams are
not just "rails."

Please advise:

- which shape you recommend
- why
- what invariants/validation rules should be enforced from day one

### 2. Exact launcher-world ownership boundary

The architect direction is clear in principle, but we still need the concrete
rule for:

- which elevated-route surfaces stay in launcher 3D
- where the single terminal board handoff truly happens

If any causal mid-route surface leaks back to the board world, the model is
wrong.

Please advise:

- the correct ownership boundary
- which surfaces/receivers must be owned by launcher 3D
- what would count as an invalid mixed-ownership design

### 3. Donor-to-collider representation

We know `RampS3`, `RampS001`, `RampS002`, and `RampS4` should become
launcher-world carriers, but we do not yet have the exact collider primitive
strategy.

Please advise:

- what primitive family should be preferred
- what should be avoided because it creates fake stability or false positives
- whether support / guard / receiver should be compiled differently

### 4. Rapier contact / stability policy

We do not want to "tune until green."

Before implementation expands, we need an explicit policy for:

- collider thickness / profile expectations
- CCD usage
- solver tuning
- when tuning is allowed
- when geometry/modeling must change instead

Please advise:

- a recommended default policy
- what tuning is acceptable during foundation work
- what red flags should stop implementation rather than invite more tuning

### 5. Observer semantics in `PR-0219`

We still need to define:

- what counts as physical occupancy evidence
- how progress should be measured against observation spines
- what divergence facts should block cut-over

Please advise:

- the minimal truthful observer contract
- which facts must be raw-row backed
- which divergence signals should become hard blockers

### 6. Temporary correction policy

The architect direction allows only a very narrow bring-up correction.

We still need to lock whether we should:

- allow a temporary entry alignment correction under strict conditions, or
- forbid it from day one

Current recommendation: allow only telemetry-visible, position-only,
non-energy-increasing correction during bring-up, with production target `0`.

Please advise:

- whether even that narrow allowance is wise
- what exact safeguards/tests/counters it would require
- whether a stricter "forbid from day one" policy is better

### 7. Baseline repin trigger

We know repin is forbidden during the foundation phase, but we still need the
exact rule for when the future physical baseline may be captured.

Current recommendation: only after focused proof, live trace, and manual
`rest` / `short` / `medium` / `full` / `relaunch` matrix all agree.

Please advise:

- the exact repin trigger you recommend
- what evidence must be present
- what should still count as blocker even if the runtime feels better manually

## Requested output

Please provide:

1. your assessment of the current implementation order
2. a recommendation for each of the seven open uncertainties above
3. any hidden dependency or blocker that the current docs do not yet capture
4. anything in `PR-0217` / `PR-0218` / `PR-0219` that should be re-scoped
   before implementation begins

Please structure your answer as:

1. implementation-order verdict
2. numbered recommendations for uncertainties 1-7
3. additional blockers / caveats
4. final advice on whether `PR-0217` is ready to start after these decisions

## High-value evidence paths

- `docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`
- `docs/backlog/reviews/review-epic-33-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md`
- `docs/backlog/epics/epic-33-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md`
- `docs/backlog/stories/story-33-01-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md`
- `docs/backlog/prs/pr-0215-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment.md`
- `docs/backlog/prs/pr-0216-flunk-out-frenzy-physical-rail-carrier-semantics-and-architect-guidance-packet.md`
- `docs/backlog/prs/pr-0217-flunk-out-frenzy-carrier-role-schema-observation-spine-contract-and-launcher-world-ownership-rules.md`
- `docs/backlog/prs/pr-0218-flunk-out-frenzy-launcher-world-carrier-compiler-and-donor-overhead-collider-foundation.md`
- `docs/backlog/prs/pr-0219-flunk-out-frenzy-physical-carrier-observer-shadow-mode-and-cutover-readiness-gate.md`
- `docs/backlog/prs/pr-0220-flunk-out-frenzy-epic-33-offline-review-packet-and-pre-implementation-decision-ask.md`
- `.agents/repomix_packages/repomix-flunk-out-frenzy-epic-33-foundation-review-context.md`
- `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`
