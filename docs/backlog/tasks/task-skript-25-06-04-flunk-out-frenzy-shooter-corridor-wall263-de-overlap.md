---
type: task
id: TASK-SKRIPT-25-06-04
title: 'Flunk-Out Frenzy: shooter-corridor Wall263 de-overlap'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-25-06-04#closeout'
story: ST-SKRIPT-25-06
task_kind: story
acceptance_criteria:
  - 'Given the lower shooter lane is already physically defined by donor `Wall95`, `Wall34`, `Wall010`, `Wall011`, `Apron1`, and `Apron2`, when this task is complete, then the `Wall263` shooter-corridor slice no longer acts as a fat `radius: 8` physical rail inside that same corridor.'
  - Given the current `outer-boundary` rail is compiled from the full donor `Wall263` chain, when this task is complete, then the shooter-lane-adjacent slice is either split out or thinned so the corridor is no longer double-defined while the donor provenance remains explicit.
  - Given the visible board still needs the full donor outline, when this task is complete, then any physical split of `Wall263` keeps the donor-backed render path inspectable and does not replace it with freehand or non-donor geometry.
  - Focused compile and physics regressions prove the lower shooter corridor is owned by the donor wall pieces rather than a fat `outer-boundary` rail segment, and a charged launch clears the previous deterministic jam region.
  - The slice records whether the launcher jam is fully solved by this geometry correction or whether `PR-0200` remains necessary for a broader donor plunger/release-path follow-up.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done, partial, on 2026-10-28 under TASK-SKRIPT-REP-0055 D6. The geometry split shipped; the Wall34 residual moved to TASK-SKRIPT-25-06-03. The original contract below is kept as history; see Closeout.

## Context

Source: `docs/backlog/prs/pr-0201-flunk-out-frenzy-shooter-corridor-wall263-de-overlap.md`. Flunk-Out Frenzy: shooter-corridor Wall263 de-overlap.

The launcher jam appears to be caused by a geometry overlap in the lower shooter lane, not only by launcher semantics. The current table spec compiles `outer-boundary` from the full donor `Wall263` chain as a physical rail with `radius: 8`, while the lower shooter corridor is already defined by donor wall solids and apron pieces. That leaves the shooter-lane slice of `Wall263` acting as a second physical boundary inside the corridor, reducing the usable gap enough to make the jam deterministic for the 24px ball. Remove the lower shooter-lane pinch by making the `Wall263` shooter-corridor slice stop acting as a fat physical rail inside the plunger lane, while keeping the donor board outline v

## Decision And Assumption Ledger

| ID                       | Type      | Status | Question/Assumption              | Recommendation/Decision                                                                            | Source                               |
| ------------------------ | --------- | ------ | -------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------ |
| MIG-TASK-SKRIPT-25-06-04 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as partial on 2026-10-28: the Wall263 split shipped, the residual Wall34 bounce moved to TASK-SKRIPT-25-06-03 (TASK-SKRIPT-REP-0055 D6). |

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

The launcher jam appears to be caused by a geometry overlap in the lower
shooter lane, not only by launcher semantics.

The current table spec compiles `outer-boundary` from the full donor `Wall263`
chain as a physical rail with `radius: 8`, while the lower shooter corridor is
already defined by donor wall solids and apron pieces. That leaves the
shooter-lane slice of `Wall263` acting as a second physical boundary inside the
corridor, reducing the usable gap enough to make the jam deterministic for the
24px ball.

### Goal

Remove the lower shooter-lane pinch by making the `Wall263` shooter-corridor
slice stop acting as a fat physical rail inside the plunger lane, while
keeping the donor board outline visible and donor-backed.

### Non-goals

- No freehand geometry or synthetic join carriers.
- No broad plunger-hardware rewrite in this slice.
- No whole-table gameplay-readiness claim beyond the focused launcher proof.

### Implementation plan

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

### Test plan

Automated:

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
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

### Rollback plan

- Restore the previous `outer-boundary` physical rail if the donor split/thin
  change introduces a worse geometry regression.
- Keep donor provenance notes and focused regression coverage so the corridor
  ownership change can be resumed cleanly.

### Progress

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
- `PhysicsWorld.launcher.spec.ts` now keeps the launcher proof focused on clearing the
  `Wall34` choke point instead of asserting the ball remains above its spawn
  position indefinitely after later playfield travel.
- Manual browser inspection on the live `:5173` route reported the expected
  geometry-only outcome for this slice: the ball is no longer deterministically
  pinched in the lower shooter corridor, but it still bounces off the exposed
  solid `Wall34` top edge instead of entering gameplay. That means `PR-0201`
  reduced the corridor overlap but did not remove the broader launcher blocker;
  `PR-0200` remains required.

### Verification notes

- `pdm run docs-validate`
- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run python - <<'PY' ...` (bootstrap-login Playwright launch trace with
  sampled `data-ball-x`/`data-ball-y`, artifacts under
  `.artifacts/flunk-out-frenzy-launch-blocker-check/`)
- Follow-up launcher-joint regression after shoulder micro-join trim:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run python - <<'PY' ...` (bootstrap-login Playwright launch sweep)
    - `.artifacts/flunk-out-frenzy-launch-blocker-check/charge-sweep-after-shoulder-trim.json`
    - `.artifacts/flunk-out-frenzy-launch-blocker-check/top-right-overlay-after-shoulder-trim.png`
- User-owned browser inspection on `http://127.0.0.1:5173/apps/games.flunk_out_frenzy` after the `PR-0201` changes:
  - the lower pinch/jam is relieved
  - the ball still hits the exposed solid `Wall34` cap and does not yet enter
    gameplay

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.

## Closeout

Closed as done, partial, on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 and D6.

TASK-SKRIPT-25-06-04 shipped the split of the donor Wall263 boundary into a `radius: 8` main rail (indices 0-44), a thin `radius: 2` right-descent rail (45-54) and a thin `radius: 2` shooter-corridor rail (54-60) with a render-only full outline, in commits 319735cb6 and 59a517af3 (`FOF/table/donor/donorPlayfieldMap.ts`, `FOF/table/spec/specPlayfieldGeometry.ts`, `compilePinballTable.donorGeometry.spec-impl.ts`). The lower-corridor pinch is relieved, but the user's browser inspection showed the ball still bounces off the exposed Wall34 top edge and does not enter gameplay; that residual moves to TASK-SKRIPT-25-06-03. The task text describes a trim to points 58..60 that is not in main (code keeps 54..60). Criterion 4 asks that a charged launch clears the previous jam region; the browser inspection did not show that, so that part of the criterion is not met here and is carried by TASK-SKRIPT-25-06-03.
