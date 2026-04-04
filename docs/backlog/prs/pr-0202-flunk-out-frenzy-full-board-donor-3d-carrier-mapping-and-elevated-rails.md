---
type: pr
id: PR-0202
title: "Flunk-Out Frenzy: full-board donor 3D carrier mapping and elevated rail fidelity"
status: blocked
owners: "agents"
created: 2026-04-03
updated: 2026-04-04
stories:
  - "ST-25-06"
tags: ["frontend", "games", "physics", "table-authoring", "donor-fidelity", "3d"]
dependencies:
  - "PR-0198"
  - "PR-0199"
  - "PR-0200"
  - "PR-0201"
  - "ST-33-01"
acceptance_criteria:
  - "Given ST-25-06 now uses the VPW donor as geometry truth, when this task is complete, then the full board-path carrier map (perimeter, lane forks, shooter chain, upper guides) is represented as explicit donor-backed 3D carriers instead of mixed legacy/local approximations."
  - "Given the donor table includes above-playfield metal/wire rail paths, when this task is complete, then those rails are represented as first-class donor-backed 3D carrier definitions with source provenance and elevation semantics rather than flattened ad hoc 2D overlays."
  - "Given the top-down render remains the user-facing board, when this task is complete, then render nodes are projected from the same donor-backed 3D carrier source of truth used by compile/physics contracts."
  - "Given anti-flattening is now a hard rule, when this task is complete, then no new laneBounds/AABB shortcuts or undocumented donor remaps are introduced for board carriers in this slice."
  - "Focused compile/physics regression coverage proves the new donor carrier map and elevated rails compile deterministically, keep provenance explicit, and do not silently reintroduce local freehand carriers."
---

## Problem

The current donor cutover contains meaningful progress, but it still leaves a
representation split:

- the launcher chain has partial 3D donor representation
- the full board-path carrier grammar is still partly expressed through
  mixed-level seams
- above-playfield metal/wire rails are not yet first-class donor-backed
  carriers in the authored/compiled table contracts

That creates drift risk each time geometry is tuned. We need one explicit donor
mapping target across board carriers and elevated rails, with no hidden
flattening shortcuts.

## Goal

Establish a true donor-fidelity carrier layer for the whole board path used by
Flunk-Out Frenzy today:

- perimeter and lane-wall chain: donor-backed and provenance-explicit
- launcher/right receiving chain: donor-backed and continuity-safe
- above-playfield metal/wire rails: donor-backed 3D carrier definitions
- compile + render projection from the same carrier truth

## Sequencing correction (2026-04-04)

This PR is now blocked for further continuation by the architect direction in
`docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`.

Specifically:

- above-playfield donor rails must compile into launcher-world or otherwise
  explicitly owned physical carriers, not be cut over by flipping current
  render-first assets in place
- the carrier-role schema and ownership model from `ST-33-01` must land before
  this PR resumes deeper physical-fidelity work

## Non-goals

- No VPX script/ROM logic import.
- No whole-table gameplay-readiness claim.
- No replacing donor geometry with local redraws.
- No broad new game-mechanics slice beyond carrier representation.

## Implementation plan

- Extend table-definition and plan contracts with explicit donor-backed 3D board
  carrier constructs for elevated rails and board-wall sections where needed.
- Add donor-map exports for above-playfield metal rails and any missing donor
  path carriers required by the screenshot-guided board path target.
- Rebuild `prototypeAlphaTableSpec.ts` so those carriers are authored once and
  projected into both compile/physics and render plans.
- Keep donor provenance (`donorSourceId` / `donorSourceIds`) explicit for every
  newly mapped board carrier.
- Add focused compile/physics tests that assert:
  - elevated rail carriers are present and donor-backed
  - board-path carrier map includes required donor chain sections
  - render output still follows compiled donor carriers

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`

Manual/live:

- user-owned browser inspection against donor screenshot path after targeted
  compile/physics proof is green

## Rollback plan

- Remove only the new PR-0202 carrier contracts and spec entries while keeping
  PR-0198/0199/0200/0201 provenance artifacts intact.
- Keep focused regression tests that capture discovered donor mapping truths so
  the slice can be resumed without rediscovery.

## Implementation status

- `prototypeAlphaVpwDonorMap.ts` now includes explicit donor-source mappings for
  the missing upper-inner metal guides (`Wall017`, `Wall002`) and above-playfield
  wire/metal rails (`RampS3`, `RampS001`, `RampS002`, `RampS4`) as provenance-backed
  3D carrier specs.
- `prototypeAlphaTableSpec.ts` now consumes those donor carriers directly:
  - upper-inner metal guide rails are first-class board rails
  - above-playfield wire rails are first-class elevated donor rails with
    donor source ids, z profiles, and render-layer separation.
- `pinballTablePlanTypes.ts` and `compilePinballTable.ts` now support elevated
  rail metadata (`zPath`, `heightBottom/heightTop`, `physics`) so donor rails
  are not silently flattened into always-colliding playfield segments.
- `staticBoardUnderlay.ts` now renders `overhead-guides` with dedicated styling
  so elevated donor carriers are visually explicit in-board.
- `compilePinballTable.spec.ts` now includes focused regressions that pin:
  - donor mapping of `Wall017` / `Wall002`
  - elevated wire-rail provenance and render behavior for `RampS3`/`S001`/`S002`/`S4`.

## Verification notes

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`

## Remaining non-donor seams

- Elevated donor rail physics remains render-first in this slice (`physics: false`)
  because full donor-faithful multi-height rail travel and handoff mechanics are
  not yet implemented end-to-end for above-playfield gameplay routing.
- Further continuation is blocked pending `ST-33-01` so the physical carrier
  cut-over does not outrun its schema/compiler/ownership foundations.
