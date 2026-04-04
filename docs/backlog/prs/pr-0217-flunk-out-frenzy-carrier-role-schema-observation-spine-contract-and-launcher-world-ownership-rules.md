---
type: pr
id: PR-0217
title: "Flunk-Out Frenzy: carrier-role schema, observation-spine contract, and launcher-world ownership rules"
status: ready
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-33-01"
tags: ["frontend", "games", "launcher", "physics", "schema", "compiler", "truth"]
dependencies:
  - "PR-0220"
  - "PR-0216"
  - "REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04"
acceptance_criteria:
  - "Given the current launcher 3D schema only knows `walls`, `guideRails`, `sensors`, and optional `travelRoutes`, when this task is complete, then authored/compiled contracts distinguish physical carrier roles from proof roles without overloading those legacy constructs."
  - "Given `travelRoutes` currently mix motion and proof semantics, when this task is complete, then the contract explicitly demotes them into observation-spine or equivalent proof-only semantics that cannot generate colliders or own motion."
  - "Given the architect guidance prefers one tagged carrier model, when this task is complete, then the launcher contract uses one tagged `carriers[]` union with explicit `kind`, explicit compile role (`physical`, `observation`, or `terminal_seam`), explicit donor provenance, and explicit `ownerWorld` with no default."
  - "Given launcher-world ownership is the decisive architectural seam, when this task is complete, then the contract defines which carrier anchors and surfaces belong to the launcher Rapier world through the one terminal board handoff and explicitly forbids duplicate donor-span ownership across worlds."
  - "Given strict seam continuity remains valuable, when this task is complete, then continuity validation survives for carrier anchors and observation spines without acting as a transport rail contract, including unique tags, connected acyclic graph validation, exactly one terminal `handoff_seam`, no mid-chain handoff seams, and preserved chained-anchor continuity."
---

## Problem

The current launcher model lacks the vocabulary needed for a truthful physical
carrier graph. It can describe walls, guide rails, sensors, and optional travel
routes, but not support/guard/receiver/handoff roles or an explicit
observation-spine proof layer.

## Goal

Create the carrier-role schema and ownership rules required before any physical
cut-over work can be honest.

## Non-goals

- No real collider cut-over yet.
- No runtime transport deletion yet.
- No baseline repin.

## Implementation plan

- Extend `tableDefinitionTypes.ts` and related compiled-plan contracts with one
  tagged `carriers[]` union instead of multiple role-specific arrays.
- Require every carrier entry to declare:
  - `kind`
  - compile role (`physical`, `observation`, or `terminal_seam`)
  - explicit donor provenance
  - explicit `ownerWorld`
- Define the observation-spine replacement for motion-owning `travelRoutes` and
  hard-fail any attempt for `observation_spine` entries to generate colliders
  or own motion.
- Encode launcher-world ownership rules and one-late-handoff topology in the
  contract/validation layer, including an explicit prohibition on duplicate
  donor-span ownership across worlds.
- Carry forward the strongest existing route validator guarantees into the new
  carrier graph:
  - unique tags
  - connected acyclic graph
  - exactly one terminal `handoff_seam`
  - no mid-chain handoff seams
  - preserved chained-anchor continuity

## Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`

## Rollback plan

- Remove only the new schema/validation contracts and preserve the architect
  reference plus blocked sequencing notes.
