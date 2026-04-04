---
type: pr
id: PR-0218
title: "Flunk-Out Frenzy: launcher-world carrier compiler and donor overhead collider foundation"
status: ready
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-33-01"
tags: ["frontend", "games", "launcher", "physics", "compiler", "donor-fidelity", "3d"]
dependencies:
  - "PR-0217"
  - "REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04"
acceptance_criteria:
  - "Given the overhead donor wireforms (`RampS3`, `RampS001`, `RampS002`, `RampS4`) are currently provenance-backed but render-only, when this task is complete, then the compiler can produce launcher-world support/guard/receiver carrier output from those donors without simply flipping top-level playfield rails to `physics: true`."
  - "Given geometry builders must remain pure, when this task is complete, then `LauncherWorldGeometry.ts` can build the new launcher-world carrier colliders without phase logic or transport policy leaking into geometry code."
  - "Given world ownership must stay explicit, when this task is complete, then the compiled output makes it clear which elevated-route surfaces are owned by the launcher Rapier world and which seam remains the terminal board handoff."
---

## Problem

The current donor overhead rails are represented and rendered, but not compiled
into the launcher-world collider model required for a truthful physical carrier
graph.

## Goal

Add the donor-backed compiler and geometry foundation for launcher-world carrier
colliders without performing the physical cut-over yet.

## Non-goals

- No runtime carrier traversal yet.
- No transport deletion yet.
- No baseline repin.

## Implementation plan

- Extend compiler output for launcher-world support/guard/receiver carrier
  colliders derived from donor geometry.
- Keep provenance explicit for compiled carrier output.
- Update `LauncherWorldGeometry.ts` to build those colliders and nothing more.
- Add focused tests that prove donor-backed collider presence and launcher-world
  ownership.

## Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`

## Rollback plan

- Remove only the new compiler/geometry carrier foundation while preserving the
  schema and sequencing corrections.
