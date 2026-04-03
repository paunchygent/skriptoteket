---
type: pr
id: PR-0201
title: "Flunk-Out Frenzy: shooter-corridor Wall263 de-overlap"
status: in_progress
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "physics", "table-authoring", "donor-fidelity", "geometry"]
dependencies:
  - "PR-0198"
acceptance_criteria:
  - "Given the lower shooter lane is already physically defined by donor `Wall95`, `Wall34`, `Wall010`, `Wall011`, `Apron1`, and `Apron2`, when this task is complete, then the `Wall263` shooter-corridor slice no longer acts as a fat `radius: 8` physical rail inside that same corridor."
  - "Given the current `outer-boundary` rail is compiled from the full donor `Wall263` chain, when this task is complete, then the shooter-lane-adjacent slice is either split out or thinned so the corridor is no longer double-defined while the donor provenance remains explicit."
  - "Given the visible board still needs the full donor outline, when this task is complete, then any physical split of `Wall263` keeps the donor-backed render path inspectable and does not replace it with freehand or non-donor geometry."
  - "Focused compile and physics regressions prove the lower shooter corridor is owned by the donor wall pieces rather than a fat `outer-boundary` rail segment, and a charged launch clears the previous deterministic jam region."
  - "The slice records whether the launcher jam is fully solved by this geometry correction or whether `PR-0200` remains necessary for a broader donor plunger/release-path follow-up."
---

## Problem

The launcher jam appears to be caused by a geometry overlap in the lower
shooter lane, not only by launcher semantics.

The current table spec compiles `outer-boundary` from the full donor `Wall263`
chain as a physical rail with `radius: 8`, while the lower shooter corridor is
already defined by donor wall solids and apron pieces. That leaves the
shooter-lane slice of `Wall263` acting as a second physical boundary inside the
corridor, reducing the usable gap enough to make the jam deterministic for the
24px ball.

## Goal

Remove the lower shooter-lane pinch by making the `Wall263` shooter-corridor
slice stop acting as a fat physical rail inside the plunger lane, while
keeping the donor board outline visible and donor-backed.

## Non-goals

- No freehand geometry or synthetic join carriers.
- No broad plunger-hardware rewrite in this slice.
- No whole-table gameplay-readiness claim beyond the focused launcher proof.

## Implementation plan

- Identify the exact donor `Wall263` drag-point range that runs down the
  shooter-lane side and overlaps the donor shooter corridor.
- Split the current `outer-boundary` representation so the shooter-corridor
  slice is no longer compiled as a `radius: 8` physical rail inside the lane.
- Keep donor provenance explicit in `prototypeAlphaVpwDonorMap.ts` and
  `prototypeAlphaTableSpec.ts`, including the donor source object and which
  slice is visual-only versus physical.
- Let donor `Wall95`, `Wall34`, `Wall010`, `Wall011`, `Apron1`, and `Apron2`
  own the lower shooter corridor physically.
- Keep the full donor `Wall263` outline visible in rendering, without drawing
  any local replacement path.
- Re-test the launch corridor before deciding whether the broader `PR-0200`
  physical-plunger rewrite is still required immediately.

## Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Focused proof expectations:

- compiled `outer-boundary` no longer creates the lower-lane pinch as a fat
  physical shooter-corridor rail
- lower shooter-corridor physical ownership comes from donor `Wall95`,
  `Wall34`, `Wall010`, `Wall011`, `Apron1`, and `Apron2`
- a charged launch clears the previously deterministic jam position

Manual/live:

- user-owned browser inspection of the launcher path after deterministic proof

## Rollback plan

- Restore the previous `outer-boundary` physical rail if the donor split/thin
  change introduces a worse geometry regression.
- Keep donor provenance notes and focused regression coverage so the corridor
  ownership change can be resumed cleanly.

## Progress

- `prototypeAlphaVpwDonorMap.ts` now splits donor `Wall263` into
  `VPW_OUTER_BOUNDARY_MAIN_PATH` plus
  `VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH` so the lower shooter-lane-adjacent
  donor slice can be represented separately without losing donor provenance.
- Follow-up corrective trim: `VPW_OUTER_BOUNDARY_SHOOTER_CORRIDOR_PATH` now
  keeps only the upper donor shoulder splice (`Wall263` points `58..60`) so
  the lower continuation toward `Wall34` is not double-defined as another
  physical corridor rail after the donor wall solids are already present.
- Additional corrective trim: the donor `Wall263` shoulder micro-join cluster
  (`points 55..57`) is now render-only. In the current thick-segment collider
  seam that micro-cluster compiled into an exposed hard blocker at the
  launcher/right-lane joint, so physical ownership now starts at point `58`
  while the full donor outline remains visible through the render surface.
- `prototypeAlphaTableSpec.ts` now compiles the main `Wall263` boundary as
  `outer-boundary-main` with `radius: 8`, and the shooter-corridor slice as
  `outer-boundary-shooter-corridor` with `radius: 2`.
- `prototypeAlphaTableSpec.ts` and `compilePinballTable.ts` now keep the full
  donor `Wall263` outline render-backed via a render-only polyline surface,
  while the split rails remain physics-only so donor render provenance stays
  intact.
- `compilePinballTable.spec.ts` now proves the split/thin physical rail
  contract explicitly, including that the lower corridor is physically owned by
  donor `Wall95`, `Wall34`, `Wall010`, `Wall011`, `Apron1`, and `Apron2`, and
  that the full donor `Wall263` outline still renders.
- `PhysicsWorld.spec.ts` now keeps the launcher proof focused on clearing the
  `Wall34` choke point instead of asserting the ball remains above its spawn
  position indefinitely after later playfield travel.
- Manual browser inspection on the live `:5173` route reported the expected
  geometry-only outcome for this slice: the ball is no longer deterministically
  pinched in the lower shooter corridor, but it still bounces off the exposed
  solid `Wall34` top edge instead of entering gameplay. That means `PR-0201`
  reduced the corridor overlap but did not remove the broader launcher blocker;
  `PR-0200` remains required.

## Verification notes

- `pdm run docs-validate`
- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run python - <<'PY' ...` (bootstrap-login Playwright launch trace with
  sampled `data-ball-x`/`data-ball-y`, artifacts under
  `.artifacts/flunk-out-frenzy-launch-blocker-check/`)
- Follow-up launcher-joint regression after shoulder micro-join trim:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run python - <<'PY' ...` (bootstrap-login Playwright launch sweep)
    - `.artifacts/flunk-out-frenzy-launch-blocker-check/charge-sweep-after-shoulder-trim.json`
    - `.artifacts/flunk-out-frenzy-launch-blocker-check/top-right-overlay-after-shoulder-trim.png`
- User-owned browser inspection on `http://127.0.0.1:5173/apps/games.flunk_out_frenzy` after the `PR-0201` changes:
  - the lower pinch/jam is relieved
  - the ball still hits the exposed solid `Wall34` cap and does not yet enter
    gameplay
