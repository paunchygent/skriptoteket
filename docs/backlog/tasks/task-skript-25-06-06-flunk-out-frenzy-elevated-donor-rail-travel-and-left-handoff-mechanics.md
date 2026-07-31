---
type: task
id: TASK-SKRIPT-25-06-06
title: 'Flunk-Out Frenzy: elevated donor rail travel and left-handoff mechanics'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: blocked
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-25-06
task_kind: story
acceptance_criteria:
- Given elevated donor rails are currently render-first, when this task is complete,
  then the launcher release path can enter a donor-backed multi-height physical carrier
  graph and stay physically supported through upper-right to upper-left handoff.
- Given donor path fidelity is required, when this task is complete, then carrier
  anchors, observation-spine phases, and handoff seams are built from donor carriers
  (`RampS3`, `RampS001`, `RampS002`, `RampS4`, and `Wall268`) with explicit source
  provenance.
- Given this slice must remove the remaining launch-path regression, when this task
  is complete, then focused physics proof shows charged launch traverses the elevated
  route and hands off leftward toward gameplay instead of immediate local bounce/fail.
- Given anti-flattening rules are active, when this task is complete, then no local
  freehand path is introduced; authored observation spines and carrier anchors stay
  donor-derived.
---

## Context

`PR-0202` made elevated donor rails first-class and provenance-backed, but left
them render-first. The live launch path still fails the donor expectation: the
ball does not reliably travel around the specified upper rail route and hand
off leftward into gameplay flow.

Implement donor-backed elevated carrier traversal/handoff mechanics so the
launch can follow the intended right-up -> top -> left feed path at multi-height
before returning to playfield flow.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

Implement donor-backed elevated carrier traversal/handoff mechanics so the
launch can follow the intended right-up -> top -> left feed path at multi-height
before returning to playfield flow.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Plan

- Build on `ST-33-01` carrier-role schema and launcher-world ownership rules.
- Compile donor-derived support/guard/receiver carriers plus observation-spine
  phases from `RampS3/S001/S002/S4` into the upper-left guide descent
  (`Wall268`) with explicit provenance and z-profile.
- Add physical carrier traversal runtime logic rather than route-follow
  transport logic:
  - enter carrier occupancy on charged release
  - observe progress/phase along the observation spine
  - perform deterministic left-hand-off at the terminal seam only
- Keep focused tests in compile/physics specs to prove carrier presence,
  observation fidelity, and left-flow traversal.

## Implementation Steps

- Build on `ST-33-01` carrier-role schema and launcher-world ownership rules.
- Compile donor-derived support/guard/receiver carriers plus observation-spine
  phases from `RampS3/S001/S002/S4` into the upper-left guide descent
  (`Wall268`) with explicit provenance and z-profile.
- Add physical carrier traversal runtime logic rather than route-follow
  transport logic:
  - enter carrier occupancy on charged release
  - observe progress/phase along the observation spine
  - perform deterministic left-hand-off at the terminal seam only
- Keep focused tests in compile/physics specs to prove carrier presence,
  observation fidelity, and left-flow traversal.

## Proof

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

## Validation

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

## Stop Conditions

- Remove only new elevated route-travel contracts/runtime and keep donor mapping
  artifacts from `PR-0202` intact.

## Lessons Learned

No separate material is recorded in the source snapshot.

## Notes

### Problem

`PR-0202` made elevated donor rails first-class and provenance-backed, but left
them render-first. The live launch path still fails the donor expectation: the
ball does not reliably travel around the specified upper rail route and hand
off leftward into gameplay flow.

### Goal

Implement donor-backed elevated carrier traversal/handoff mechanics so the
launch can follow the intended right-up -> top -> left feed path at multi-height
before returning to playfield flow.

### Sequencing correction (2026-04-04)

This PR is now blocked for further continuation by the architect direction in
`docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`.

The old route-driven cut-over assumption is no longer valid. When this PR
eventually resumes:

- `travelRoutes` must be observation spines only
- physical motion must belong to the carrier graph, not a route runner
- continuation must build on `EPIC-33` / `ST-33-01`, not bypass it

### Non-goals

- No whole-table gameplay readiness claim.
- No VPX script/ROM import.
- No freehand replacement geometry.

### Implementation plan

- Build on `ST-33-01` carrier-role schema and launcher-world ownership rules.
- Compile donor-derived support/guard/receiver carriers plus observation-spine
  phases from `RampS3/S001/S002/S4` into the upper-left guide descent
  (`Wall268`) with explicit provenance and z-profile.
- Add physical carrier traversal runtime logic rather than route-follow
  transport logic:
  - enter carrier occupancy on charged release
  - observe progress/phase along the observation spine
  - perform deterministic left-hand-off at the terminal seam only
- Keep focused tests in compile/physics specs to prove carrier presence,
  observation fidelity, and left-flow traversal.

### Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

### Rollback plan

- Remove only new elevated route-travel contracts/runtime and keep donor mapping
  artifacts from `PR-0202` intact.

### Progress

- Added a donor-backed launcher travel-route artifact in
  `prototypeAlphaVpwDonorMap.ts` by composing
  `RampS3/RampS001/RampS002/RampS4` into one provenance-backed elevated route
  (`VPW_LAUNCH_TRAVEL_ROUTE_OVERHEAD_3D_PATH`), with `Wall268` still
  represented as board-owned donor guide descent after handoff.
- Wired that route into authored table contracts in
  `prototypeAlphaTableSpec.ts` through `launcher.threeD.travelRoutes` without
  introducing freehand points.
- Implemented route-follow and deterministic left-handoff runtime behavior in
  `launcherChain3d.ts` and integrated launcher-chain ownership into
  `PhysicsWorld.ts` so launch-phase balls run through the donor route before
  board handoff.
- Added focused compile/physics proof updates in
  `compilePinballTable.spec.ts` and `PhysicsWorld.launcher.spec.ts` for route presence
  and left-flow traversal.

### Verification Notes

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

### Residual Risk

- This slice proves donor-route traversal/handoff behavior in focused runtime
  checks, but it does not claim full-table gameplay readiness.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
