---
type: epic
id: EPIC-SKRIPT-25
title: 'Curated app family: competitive games foundations and Flunk-Out Frenzy'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Signed-in users can open Flunk-Out Frenzy as a bespoke curated app, play
  a polished local browser-based experience inside the existing Skriptoteket SPA,
  deepen the local runtime with richer pinball-like mechanics without collapsing architecture
  boundaries, and retain the backend seams required to add lightweight global high
  scores without rewriting the app contract.
retired_ids:
- EPIC-25
---

## Scope

### Scope

- **Family architecture**: establish the competitive-games curated-app shape so
  future games can reuse the same competition backend seams.
- **Flunk-Out Frenzy app**: introduce the first game as a bespoke curated app
  under the existing app host.
- **Frontend runtime**: keep live simulation browser-owned and isolated from the
  generic tool-run/session UI model.
- **Mechanics fidelity**: deepen the local game runtime with bounded physics,
  table-authoring, and rule seams that can absorb richer device semantics
  without copying a donor engine architecture.
- **Backend substrate**: reserve the models and API contracts needed for pending
  score submission, lightweight leaderboard acceptance, and leaderboard queries.

### Out of scope

- Multiple game apps shipping in the same slice
- Tournament administration
- Social graph or chat
- Mobile-first controls
- Real-time multiplayer
- Redis/WebSocket infrastructure as a hard requirement
- A wholesale native-engine port or emulator path for Flunk-Out Frenzy

### Risks

- The first game could accidentally couple itself to one-off persistence paths.
- A weak score/ruleset contract could make later leaderboard support expensive
  to add safely.
- The frontend could drift into Vue-owned simulation state if the shell/runtime
  boundary is not enforced.

### Stories

- [x] [ST-25-01: Competitive games substrate and Flunk-Out Frenzy bootstrap contract](../stories/story-25-01-competitive-games-substrate-and-flunk-out-frenzy-bootstrap-contract.md)
- [x] [ST-25-02: Flunk-Out Frenzy local runtime vertical slice](../stories/story-25-02-flunk-out-frenzy-local-runtime-vertical-slice.md)
- [ ] [ST-25-03: Competitive play lightweight score submission and typed leaderboards](../stories/story-25-03-competitive-play-pending-score-submission-and-typed-leaderboards.md)
- [ ] [ST-25-04: Competitive play lightweight leaderboard hardening and ruleset scoping](../stories/story-25-04-competitive-play-leaderboard-hardening-and-ruleset-scoping.md)
- [ ] [ST-25-05: Flunk-Out Frenzy mechanics-port foundation](../stories/story-25-05-flunk-out-frenzy-mechanics-port-foundation.md)
- [ ] [ST-25-06: Flunk-Out Frenzy VPW donor topology and table-spec rebuild](../stories/story-25-06-flunk-out-frenzy-vpw-donor-topology-and-table-spec-rebuild.md)

### Notes

- **First implementation slice**: ST-25-01 and ST-25-02.
- **Planned from the start**: ST-25-03 and ST-25-04 define the competition path
  that the local slice must remain compatible with.
- **Follow-on local depth**: ST-25-05 deepens the browser-local mechanics
  substrate without taking a dependency on pending-score persistence.
- **ST-25-05 execution gate**: `PR-0188` through `PR-0190` form the first
  foundation tranche, `PR-0191` is a formal reassessment and go/no-go
  checkpoint, and only then do the higher-risk mechanics slices begin.
- **Board corrective gate**: `ST-25-06` / `PR-0198` track the donor-topology
  rebuild needed before higher-risk mechanics slices can continue safely on the
  compiled table seam, `PR-0199` owns trigger/gate and lane-region semantic
  fidelity, and `PR-0201` owns the lower shooter-corridor `Wall263`
  de-overlap correction.
- **Physical-carrier foundation gate**: further continuation of `PR-0200`,
  `PR-0202`, and `PR-0203` is now blocked on `EPIC-33` /
  `ST-33-01`, which owns the carrier-role schema, launcher-world ownership
  rules, donor overhead collider foundation, and observer/cut-over governance
  required by the architect direction.
- Cross-cutting sequencing beyond this epic is tracked in
  `docs/reference/ref-competitive-games-cross-cutting-programme.md`.

### Implementation Summary (as of 2026-04-01)

- `ST-25-05` tranche-one foundation (`PR-0188`, `PR-0189`, `PR-0190`) is
  complete: `PhysicsWorld` and `RuleEngine` are decomposed into modular seams,
  machine-event vocabulary is widened, and pure rule-state modules own bonus,
  jackpot, and ball-lifecycle logic.
- `PR-0191` reassessment returned a **GO** decision: the architecture is stable,
  file-size targets are met, and the runtime boundary is verified as ready for
  the higher-fidelity mechanics tranche.

### Implementation Summary (as of 2026-04-03)

- `ST-25-06` is now governed by a stricter donor-fidelity rule: lane and
  launcher semantics are no longer allowed to rely on flattened `laneBounds`
  or other AABB containment shortcuts when the donor defines shaped lane
  regions.
- `PR-0198` remains the donor topology / board-carrier cutover, while
  `PR-0199` explicitly owns replacing the remaining lane-shape flattening seams
  with donor-shaped lane-region semantics across the launcher corridor and
  related board lanes.
- `PR-0200` now explicitly owns the Rapier 3D launcher-chain migration so the
  browser model stops treating the launcher choke point as a flat impulse-path
  problem.
- `PR-0201` now explicitly owns the geometry-first corrective slice before the
  broader launcher rewrite: split or thin the `Wall263` shooter-corridor slice
  so donor `Wall95`, `Wall34`, `Wall010`, `Wall011`, `Apron1`, and `Apron2`
  own the lower shooter lane physically.
- `PR-0202` now explicitly owns the full-board donor 3D carrier map and
  elevated metal/wire rail representation so the board-path target can be
  validated against donor truth without local redraw seams.
- `PR-0203` now explicitly owns runtime traversal/handoff along donor elevated
  rail carriers (`RampS3/S001/S002/S4` + `Wall268` descent) so launcher flow is
  not left to perimeter bounce artifacts.

### Implementation Summary (as of 2026-04-04)

- The architect direction in
  `docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`
  now governs any future launcher physical-rail cut-over.
- `PR-0215` is tightened to a runtime-honesty checkpoint only; it is no longer
  the implied vehicle for full physical-carrier implementation.
- New `EPIC-33` / `ST-33-01` now slot ahead of further cut-over work and own
  the carrier-role schema, launcher-world ownership model, donor overhead
  collider foundation, and observer/cut-over readiness gate.
- `PR-0200`, `PR-0202`, and `PR-0203` remain part of the longer launcher
  corrective lane, but their further continuation is now explicitly blocked on
  that foundation so no slotted task continues under stale route-driven
  assumptions.

### Implementation Summary (as of 2026-03-23)

- `ST-25-01` shipped the Flunk-Out Frenzy curated-app registration,
  discoverability, bespoke route resolution, and minimal typed bootstrap
  contract.
- `ST-25-02` shipped the immersive game-first shell, runtime/core boundary,
  Rapier-backed prototype-alpha physics/rules, and the first playable local
  Pixi/Howler 3-ball slice with verified pause/restart/mute and route disposal.

## Epic Contract

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Stories

The source material below remains authoritative for this section.

## Epic Verification Plan

Verification expectations remain in the retained source material below.

## Exceptions And Follow-Ups

The source boundaries and recovery limits remain preserved below.

## Risks

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Epic Closeout Review

The source material below remains authoritative for this section.
