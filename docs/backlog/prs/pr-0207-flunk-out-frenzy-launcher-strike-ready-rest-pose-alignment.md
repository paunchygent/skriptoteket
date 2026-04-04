---
type: pr
id: PR-0207
title: "Flunk-Out Frenzy: proof-first launcher strike root-cause gate and seam-contract lock"
status: ready
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "root-cause", "deterministic-proof", "no-shortcuts"]
dependencies:
  - "PR-0200"
  - "PR-0206"
acceptance_criteria:
  - "Given PR-0206 proved `no_effective_strike` under full-charge release, when this task is complete, then telemetry and tests deterministically classify whether failure is pre-contact pose mismatch or post-contact route-capture gating, without production geometry/runtime behavior edits."
  - "Given no-shortcuts invariants are non-negotiable, when this task is complete, then no direct launch `setLinvel(...)` shortcut, no synthetic launch gate events, no seam-tolerance relaxation, and no helper/freehand seam geometry are introduced."
  - "Given the launcher seam contract must remain donor-faithful, when this task is complete, then endpoint-bridge authoring remains exactly `[overheadExitAnchor, descentEntryAnchor]` (two points only) with no intermediate bridge points, no helper rails, and no freehand seam geometry."
  - "Given this task is proof-first only, when this task is complete, then the unchanged full PR-0206 matrix (`rest`, `short`, `medium`, `full`, `relaunch`) is executed under identical thresholds, step budgets, and case set, and any red outcomes remain explicit evidence instead of being greened by production behavior changes."
  - "Given swplunger/sw16 semantic separation is hard-required, when this task is complete, then `swplunger` remains feed/rest anchor and `sw16` remains exit anchor with real exit transition semantics."
  - "Given handoff consistency is required, when this task is complete, then docs and handoff notes contain no conflicting guidance about scope, invariants, or evidence expectations."
---

## Problem

PR-0206 telemetry and tests now show the launch defect is not primarily input wiring. Under full-charge release, the ball receives no effective plunger strike (`no_effective_strike`) and route capture remains rejected (`distance_xy`) because strike-ready rest/serve alignment is not satisfied.

## Goal

Lock a proof-first gate that pinpoints the launcher root cause with deterministic telemetry/tests and explicit seam contracts before any production geometry/runtime behavior fix is allowed.

## Non-goals

- No production geometry or runtime behavior fixes in this task.
- No whole-table architecture rewrite.
- No seam tolerance relax (`xy<=1`, `z<=1` stays strict).
- No helper rails or freehand seam bridge geometry.
- No invented intermediate endpoint-bridge points (bridge remains exactly two donor anchors).
- No runtime velocity shortcut (`setLinvel`) as launch substitute.
- No synthetic `gate-passed` semantics from route start.

## Root-cause scope (bounded)

Primary edit scope (tests/telemetry/docs only):

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
- `.agents/handoff.md`

Secondary proof scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorMap.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`

Explicit out-of-scope clarification:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts` is out of scope for behavior changes in this task.
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts` is out of scope unless a separately reviewed task first makes it the live authoritative launcher seam.
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorDevices.ts` is out of scope for production authoring edits in this task.

## Implementation plan

1. Lock authored seam contract in compile-time proof (no authoring edits):
   - Assert endpoint-bridge contract remains exact and explicit:
     - bridge path is exactly `[overheadExitAnchor, descentEntryAnchor]`
     - bridge path length is exactly `2`
     - no intermediate/smoothing points are allowed
   - Assert perturbation evidence:
     - if either anchor is perturbed by `>1px` in compile-test fixtures, seam validation fails
   - Preserve donor ownership boundaries and route chain identity (`overhead -> endpoint-bridge -> descent`) as authored.

2. Add deterministic rest-contract assertions:
   - At fed/rest state, enforce strike-observability conditions in proof:
     - feed sensor occupancy at serve baseline (`feedInside = true`)
     - exact rest-separation predicate:
       - `separationPx = plungerFrontFaceY - (ballY + ballRadius)`
       - required assertion-only bound at fed/rest baseline: `0 <= separationPx <= 2`
   - this bound is proof-only and must not be reused as runtime tolerance, route-capture relaxation, seam-tolerance adjustment, or production behavior switch.
   - Keep these as testable invariants, not runtime heuristics.

3. Preserve PR-0206 matrix as unchanged truth source:
   - Use unchanged PR-0206 fixed parameters:
     - `dtMs=16`, `holdSteps=8/26/56`, `relaunchGapSteps=16`, `observationSteps=60`
   - Use unchanged PR-0206 thresholds:
     - short: displacement `>=2`, `minVy<=-8`
     - medium: displacement `>=4`, `minVy<=-20`
     - full: displacement `>=8`, `minVy<=-40`
   - Required matrix outcomes:
     - all cases (`rest`, `short`, `medium`, `full`, `relaunch`) must run under unchanged case definitions and thresholds.
     - no threshold, step-budget, case-set, or artifact-schema modifications are allowed in this task.
     - any remaining red cases must be retained as explicit failure evidence with stable reason-codes/telemetry fields.

4. Preserve no-shortcuts and seam semantics:
   - Keep route-entry and sw16 semantics tied to physical transitions.
   - Keep terminal-route-only handoff semantics.
   - Do not introduce fallback behaviors that bypass physical strike.
   - Do not modify production geometry/runtime files to force green outcomes.

## Test plan

- Focused deterministic proof suite:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
  - include unchanged PR-0206 artifact/schema assertions (including forbidden `gate-passed` field) in the same focused proof surfaces.
- Contract and integration gates:
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run docs-validate`

## Live verification (required)

- Run launcher matrix on:
  - `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Retain artifacts under:
  - `.artifacts/flunk-out-frenzy-launcher-root-cause-proof/`
- Record commands and observed results in:
  - `.agents/handoff.md`

## Reviewer checklist

- Task remains proof-first only; no production geometry/runtime behavior changes are authorized.
- Endpoint-bridge contract is explicit and strict: exactly `[overheadExitAnchor, descentEntryAnchor]` and exactly two points.
- PR-0206 matrix and telemetry schema remain unchanged and are executed as evidence, not tuned to force green.
- Seam invariants and swplunger/sw16 semantics remain intact.
- No forbidden fields or synthetic event aliases are added to launcher proof artifacts.

## Non-negotiable stop conditions

Do not mark complete if any remain true:

- any production geometry/runtime behavior file is changed to force matrix outcomes
- endpoint-bridge contract is not explicitly asserted as exact two-anchor/two-point seam
- unchanged PR-0206 thresholds/steps/case-set/artifact schema are modified
- any direct velocity launch shortcut is reintroduced
- seam continuity/tolerance rules are weakened
- conflicting scope guidance remains in task/handoff documentation
