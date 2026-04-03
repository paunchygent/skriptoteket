---
type: pr
id: PR-0200
title: "Flunk-Out Frenzy: Rapier 3D launcher-chain migration"
status: in_progress
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "physics", "table-authoring", "launcher", "donor-fidelity", "3d"]
dependencies:
  - "PR-0198"
  - "PR-0199"
  - "PR-0201"
acceptance_criteria:
  - "Given the current Flunk-Out Frenzy runtime expresses donor launcher flow through a flat impulse-and-solid model, when this task is complete, then the launcher/right-side receiving chain runs on a dedicated Rapier 3D simulation path that can represent donor height, plunger stroke, and wall-face truth directly."
  - "Given the current live board makes donor `Wall34` a false full cap across the shooter path, when this task is complete, then `Wall34`, `Wall95`, `Wall011`, `Wall010`, the `Wall263` right shoulder, `Wall264`, and `Wall018`/`Wall019` are represented in 3D with the donor-authored launcher handoff preserved instead of flattened into plain flat blockers."
  - "Given donor launcher semantics currently span `PlungerRose`, `swplunger`, and `sw16`, when this task is complete, then those donor objects have explicit authored provenance and distinct 3D runtime roles for rest, pullback, stroke, release, and exit semantics."
  - "Given `PR-0201` already removed the lower shooter-lane pinch, when this task is complete, then the remaining launcher failure is resolved by truthful 3D representation rather than by further force tuning, synthetic join carriers, or another flat approximation."
  - "Given the current renderer is top-down and browser-owned, when this task is complete, then the 3D launcher simulation still feeds the existing top-down render pipeline through an explicit compiled seam instead of coupling presentation directly to Rapier internals."
  - "Focused compile, physics, and browser regressions prove a charged launch clears the exposed `Wall34` blocker and enters the donor right-side receiving chain, and the slice records no broader gameplay-ready claim beyond that proof."
---

## Problem

The remaining launcher blocker is not a tuning issue and not a missing donor
object.

The live code makes donor `Wall34` a full rectangular solid and therefore a
full blocking cap across the shooter path. That happens because the launcher
chain is still expressed through flat convex
polygons and an impulse/state-machine launcher instead of donor-faithful
launcher hardware and height-aware wall geometry.

`PR-0201` proved the lower corridor overlap was real and worth fixing, but it
also proved that geometry de-overlap alone is not enough: once the lower pinch
is relieved, the ball still reaches the false `Wall34` cap created by the
flattened flat-physics representation.

That means the remaining problem is not "more careful flat geometry." It is that the
launcher chain is currently modeled in the wrong dimensionality.

## Goal

Migrate the launcher/right-side receiving flow to an explicit Rapier 3D seam so
the donor launcher handoff can be expressed honestly:

- donor plunger hardware as a real 3D plunger body/stroke
- donor-authored rest/feed/pullback/release/exit semantics across
  `PlungerRose`, `swplunger`, and `sw16`
- donor wall heights and exposed faces for `Wall34`, `Wall95`, `Wall011`,
  `Wall010`, the `Wall263` shoulder, `Wall264`, and `Wall018`/`Wall019`
- a compiled seam that lets the existing top-down renderer stay intact while
  the launcher chain stops being flattened into false flat blockers

## Non-goals

- No VPX script or ROM rule import.
- No whole-table 3D migration in one step.
- No presentation-layer rewrite away from the current top-down board renderer.
- No gameplay-readiness claim for the whole table; this task closes the
  launcher/right-side 3D representation gap only.

## Implementation plan

- Introduce a dedicated 3D launcher-chain contract in `tableDefinitionTypes.ts`
  and `pinballTablePlanTypes.ts` for:
  - donor plunger hardware (`PlungerRose`)
  - donor launcher sensors (`swplunger`, `sw16`)
  - donor 3D wall sections/faces in the right-side launcher chain
  - explicit authored provenance for every migrated donor object
- Add a launcher-chain-specific compiled plan in `compilePinballTable.ts` that
  stands on its own:
  - 3D rigid bodies/colliders/joints for plunger hardware and launcher-chain
    walls
  - a top-down projection seam for renderer/debug visibility
  - explicit mapping between 3D contacts/events and existing machine-event
    semantics
- Migrate `PhysicsWorld.ts` to `@dimforge/rapier3d-compat` for the launcher and
  right-side receiving flow. Do not preserve a mixed-dimensional launcher seam
  or reintroduce flat fallback geometry anywhere inside that donor chain.
- Replace the current launcher impulse/state-machine seam in
  `plungerLaneState.ts` with donor-backed plunger pullback/stroke/release logic
  that physically contacts and feeds the ball through the 3D launcher path.
- Re-express donor `Wall34` and its immediate chain neighbors as truthful 3D
  geometry/faces instead of full false-flat caps. If a donor object needs
  a partial face, height, or non-flat contact surface, model that directly.
- Keep `PR-0201` geometry correction intact where it remains valid, but delete
  any remaining launcher-local flat shortcut that survives only because the old
  impulse model needed it.
- Defer non-launcher elevated donor pieces such as `Wall024` unless they become
  direct blockers in the launcher/right-side proof.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Focused proof expectations:

- compiled launcher-chain definitions preserve donor provenance for
  `PlungerRose`, `swplunger`, `sw16`, `Wall34`, `Wall95`, `Wall011`, `Wall010`,
  the `Wall263` shoulder, `Wall264`, and `Wall018`/`Wall019`
- the 3D launcher proof shows why `Wall34` is no longer a false full cap in the
  live simulation
- a charged launch clears the current `Wall34` blocker and enters the donor
  right-side receiving chain without synthetic impulse assist or non-donor
  join geometry
- the proof demonstrates a real plunger-body/stroke contact path, not a
  disguised vertical-impulse shortcut

Manual/live:

- user-owned browser inspection of the launcher/right-side receiving flow after
  deterministic proof is green

## Rollback plan

- Remove the new 3D launcher-chain contracts and restore the current geometry
  checkpoint only if the Rapier 3D seam cannot be stabilized quickly.
- Keep the donor provenance mapping and focused regression coverage so the 3D
  launcher migration can be resumed without re-discovery.

## Implementation status

- Local implementation currently runs on a single Rapier 3D world seam in
  `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`.
  The checked-in `launcherChain3d.ts` helper exists in-tree but is not the live
  runtime seam for this slice.
- The authored/compiled contracts now carry donor-backed 3D launcher data in
  `tableDefinitionTypes.ts`, `pinballTablePlanTypes.ts`,
  `prototypeAlphaVpwDonorDevices.ts`, `prototypeAlphaTableSpec.ts`, and
  `compilePinballTable.ts`.
- `PlungerRose`, `swplunger`, `sw16`, `Wall95`, `Wall34`, `Wall011`,
  `Wall010`, the `Wall263` shoulder, `Wall264`, and `Wall018`/`Wall019` now
  have explicit launcher-chain provenance in the authored table slice.
- The temporary hardcoded right-bias release vector in `PhysicsWorld.ts` is now
  removed. Release velocity now uses authored launcher semantics directly
  (`x = launcher.launchAssistX`, `y = -speed`) so launcher flow is no longer
  held together by non-donor ad hoc shove constants.
- Known gap (still open): release is still applied through a direct
  `ballBody.setLinvel(...)` shortcut on `launcher-released` rather than a proven
  plunger-body contact strike. This PR remains `in_progress` until that physical
  contact-path contract is implemented or explicitly re-scoped.
- The browser route on `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
  initially failed because the running frontend container could not resolve the
  new `@dimforge/rapier3d-compat` dependency. Refreshing the container install
  with `docker exec windsurf-project-frontend-1 pnpm -C /app/frontend install`
  restored module resolution and let the live route reach `ready`.
- This slice does not claim whole-table gameplay readiness. The verified live
  browser result is limited to successful runtime startup and renderer mount on
  `5173`; broader feel/play validation remains outside this PR.

## Verification notes

- `pdm run fe-type-check`
- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-build`
- `docker exec windsurf-project-frontend-1 pnpm -C /app/frontend install`
- `pdm run python - <<'PY' ...` (bootstrap-login Playwright launcher trace
  sampling `data-ball-x`/`data-ball-y` during charged release):
  - `.artifacts/flunk-out-frenzy-launch-blocker-check/samples.json`
  - `.artifacts/flunk-out-frenzy-launch-blocker-check/samples-no-bias.json`
  - `.artifacts/flunk-out-frenzy-launch-blocker-check/after-launch.png`
  - `.artifacts/flunk-out-frenzy-launch-blocker-check/after-launch-no-bias.png`
- One-off Playwright check against `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
  using the bootstrap superuser:
  - verified `data-runtime-load-state="ready"`
  - verified `[data-test="runtime-renderer-canvas"]` is visible
  - wrote `.artifacts/flunk-out-frenzy-route-check-pr0200/flunk-out-frenzy-route-pr0200.png`

## Review notes

- Latest `skriptoteket_reviewer` pass returned `changes_requested` with one
  high-priority contract gap still open: launcher release still uses a direct
  velocity write instead of a demonstrated physical plunger strike.
- Additional reviewer-required cleanups:
  - keep runtime architecture claims aligned with the current single-world
    `PhysicsWorld` implementation (no stale “wired launcherChain3d seam” wording)
  - avoid over-claiming browser gameplay proof from coordinate-only traces
  - keep the `Wall263` shoulder truncation pinned by focused regression coverage
