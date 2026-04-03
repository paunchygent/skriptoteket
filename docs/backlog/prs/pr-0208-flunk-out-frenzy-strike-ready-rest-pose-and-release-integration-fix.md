---
type: pr
id: PR-0208
title: "Flunk-Out Frenzy: strike-ready rest-pose alignment and release-contact integration fix"
status: ready
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "root-cause", "physics", "proof-first", "no-shortcuts"]
dependencies:
  - "PR-0206"
  - "PR-0207"
acceptance_criteria:
  - "Given `PR-0207` proof remains authoritative, when this task is complete, then the launcher feed/rest baseline satisfies strike-ready rest pose (`feedInside=true`, `0<=separationPx<=2`) through production mechanics, not through assertion changes."
  - "Given full-charge inert behavior is still unresolved, when this task is complete, then full-charge release meets unchanged `PR-0206` launch-effect threshold (`minVy<=-40`) without relaxing proof thresholds, case set, or observation windows."
  - "Given no-shortcuts invariants are hard requirements, when this task is complete, then no direct launch `setLinvel(...)` shortcut, no synthetic `gate-passed` route-start emission, and no route-start teleport substitute are introduced."
  - "Given donor seam invariants are non-negotiable, when this task is complete, then endpoint-bridge authoring remains exact `[overheadExitAnchor, descentEntryAnchor]`, seam continuity remains `xy<=1/z<=1`, and no helper/freehand seam geometry is added."
  - "Given launcher semantics must remain explicit, when this task is complete, then `swplunger` remains feed/rest anchor and `sw16` remains real exit anchor with physical transition semantics."
  - "Given this is a bounded launcher seam fix, when this task is complete, then implementation scope is limited to launcher-chain release/contact mechanics plus focused proof/spec updates needed to keep contract checks strict and typed."
  - "Given UI/route workflow rules require evidence, when this task is complete, then focused verification and live launcher route checks are recorded in `.agents/handoff.md`."
---

## Problem

Focused verification on 2026-04-03 is red on two launcher root-cause proofs:

1. Full-charge proof fails velocity threshold:
   - observed `minVy=-17.0166` vs required `<=-40`.
2. Rest baseline fails strike-ready separation:
   - observed `separationPx=-8.9433` vs required `0..2`.

This shows the unresolved defect is still in physical strike readiness/release-contact integration, not in proof thresholds.

## Goal

Fix the verified launcher root cause by making the fed/rest ball-plunger pose strike-ready and making release-time contact integration deterministic at the physics seam, while preserving all existing seam and semantic invariants.

## Non-goals

- No seam tolerance relaxation (`xy<=1`, `z<=1` remains strict).
- No helper rails, no freehand seam geometry, no invented bridge points.
- No whole-table architecture rewrite.
- No conversion of launch release into direct velocity writes or synthetic gate events.
- No changes to `PR-0206`/`PR-0207` matrix thresholds, steps, case set, or artifact-schema contract.

## Root-cause scope (bounded)

Primary implementation scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`

Focused proof/support scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `.agents/handoff.md`

Out of scope:

- donor route authoring files (`prototypeAlphaVpwDonorMap.ts`, `prototypeAlphaTableSpec.ts`)
- seam compiler contract files beyond existing checks
- board geometry/topology changes

## Implementation plan

1. Strike-ready rest alignment (production mechanics, no threshold edits):
   - On launcher-chain ball ownership/spawn, align ball Y to a strike-ready rest pose derived from plunger front face:
     - `plungerFrontFaceY = plungerCenterY - plungerDepth/2`
     - `ballRestY = plungerFrontFaceY - ballRadius - restGapPx`
   - Use a fixed donor-space rest gap target (`restGapPx=1`) to satisfy proof contract `0<=separationPx<=2`.
   - Keep donor feed semantics unchanged (`swplunger` remains feed/rest anchor).

2. Release-contact integration fidelity (physical, no shortcut impulse write):
   - Keep release contact plunger-driven via kinematic plunger body.
   - Add bounded post-release physics substep integration window so plunger-body strike resolves deterministically:
     - substep interval `4ms`
     - bounded window `64ms` after release intent
   - Keep route entry and route handoff semantics unchanged (no route-start gate synthesis, no mid-chain handoff).

3. Contact telemetry robustness (non-behavioral semantics preserved):
   - Preserve contact entry/exit event markers.
   - Aggregate per-step overlap/relative-contact velocity across release substeps for deterministic telemetry evidence.

4. Keep proof contracts strict and typed:
   - Fix nullable proof typing in `PhysicsWorld.spec.ts` by asserting/guarding required telemetry fields (no `number|null` silent coercion).
   - Do not relax or delete any existing failing assertions.

## Test plan

- Focused regression commands:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts src/components/apps/flunk-out-frenzy/game/core/GameRuntime.spec.ts src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run docs-validate`

- Required proof expectations:
  - rest proof remains strict and turns green through mechanics (`0<=separationPx<=2`)
  - full-charge proof remains strict and turns green through mechanics (`minVy<=-40`)
  - unchanged matrix case contracts remain intact
  - no synthetic `gate-passed` alias and no direct release `setLinvel(...)` path

## Live verification (required)

- URL:
  - `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Cases:
  - rest, short tap, medium hold, full charge, repeated relaunch
- Required observations:
  - visible plunger motion
  - visible ball response
  - lane progression to real `sw16` exit semantics
  - no false gate at served rest
- Record exact commands and observations in `.agents/handoff.md`.

## Non-negotiable stop conditions

Do not mark complete if any remain true:

- rest separation proof still fails (`separationPx<0` or `>2`)
- full-charge proof still fails unchanged threshold (`minVy>-40`)
- any direct launch velocity shortcut is introduced
- any seam tolerance/bridge contract is relaxed
- `sw16` gate semantics are synthesized from route start
- verification evidence is missing from `.agents/handoff.md`
