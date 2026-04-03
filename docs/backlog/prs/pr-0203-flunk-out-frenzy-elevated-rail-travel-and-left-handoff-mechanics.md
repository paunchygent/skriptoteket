---
type: pr
id: PR-0203
title: "Flunk-Out Frenzy: elevated donor rail travel and left-handoff mechanics"
status: in_progress
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "physics", "table-authoring", "donor-fidelity", "3d", "launcher"]
dependencies:
  - "PR-0200"
  - "PR-0201"
  - "PR-0202"
acceptance_criteria:
  - "Given elevated donor rails are currently render-first, when this task is complete, then the launcher release path can enter a donor-backed multi-height travel route and stay on that route through upper-right to upper-left handoff."
  - "Given donor path fidelity is required, when this task is complete, then route segments and handoff anchors are built from donor carriers (`RampS3`, `RampS001`, `RampS002`, `RampS4`, and `Wall268`) with explicit source provenance."
  - "Given this slice must remove the remaining launch-path regression, when this task is complete, then focused physics proof shows charged launch traverses the elevated route and hands off leftward toward gameplay instead of immediate local bounce/fail."
  - "Given anti-flattening rules are active, when this task is complete, then no local freehand path is introduced; authored route points stay donor-derived."
---

## Problem

`PR-0202` made elevated donor rails first-class and provenance-backed, but left
them render-first. The live launch path still fails the donor expectation: the
ball does not reliably travel around the specified upper rail route and hand
off leftward into gameplay flow.

## Goal

Implement donor-backed elevated rail travel/handoff mechanics so the launch can
follow the intended right-up -> top -> left feed path at multi-height before
returning to playfield flow.

## Non-goals

- No whole-table gameplay readiness claim.
- No VPX script/ROM import.
- No freehand replacement geometry.

## Implementation plan

- Extend launcher 3D contracts with explicit donor-backed travel route
  definitions (path, provenance, charge threshold, handoff semantics).
- Build a donor-derived launch travel route from `RampS3/S001/S002/S4` into the
  upper-left guide descent (`Wall268`) with explicit z-profile.
- Add route-travel runtime logic in `PhysicsWorld.ts`:
  - enter route on charged release
  - follow route at multi-height
  - perform deterministic left-hand-off at route exit
- Keep focused tests in compile/physics specs to prove route presence and
  behavior.

## Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

## Rollback plan

- Remove only new elevated route-travel contracts/runtime and keep donor mapping
  artifacts from `PR-0202` intact.

## Progress

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
  `compilePinballTable.spec.ts` and `PhysicsWorld.spec.ts` for route presence
  and left-flow traversal.

## Verification Notes

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

## Residual Risk

- This slice proves donor-route traversal/handoff behavior in focused runtime
  checks, but it does not claim full-table gameplay readiness.
