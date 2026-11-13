---
type: task
id: TASK-SKRIPT-33-01-01
title: 'Flunk-Out Frenzy: carrier-role schema, observation-spine contract, and launcher-world ownership rules'
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
  approval_evidence: 'TASK-SKRIPT-33-01-01#closeout'
story: ST-SKRIPT-33-01
task_kind: story
acceptance_criteria:
  - Given the current launcher 3D schema only knows `walls`, `guideRails`, `sensors`, and optional `travelRoutes`, when this task is complete, then authored/compiled contracts distinguish physical carrier roles from proof roles without overloading those legacy constructs.
  - Given `travelRoutes` currently mix motion and proof semantics, when this task is complete, then the contract explicitly demotes them into observation-spine or equivalent proof-only semantics that cannot generate colliders or own motion.
  - Given the architect guidance prefers one tagged carrier model, when this task is complete, then the launcher contract uses one tagged `carriers[]` union with explicit `kind`, explicit compile role (`physical`, `observation`, or `terminal_seam`), explicit donor provenance, and explicit `ownerWorld` with no default.
  - Given launcher-world ownership is the decisive architectural seam, when this task is complete, then the contract defines which carrier anchors and surfaces belong to the launcher Rapier world through the one terminal board handoff and explicitly forbids duplicate donor-span ownership across worlds.
  - Given strict seam continuity remains valuable, when this task is complete, then continuity validation survives for carrier anchors and observation spines without acting as a transport rail contract, including unique tags, connected acyclic graph validation, exactly one terminal `handoff_seam`, no mid-chain handoff seams, and preserved chained-anchor continuity.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

## Context

The source does not provide a separate context section; no additional context is recorded.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Story Contract Slice

### Source: Goal

Create the carrier-role schema and ownership rules required before any physical
cut-over work can be honest.

## Contract Inputs

The source does not provide a separate contract inputs section; no additional contract inputs is recorded.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

### Source: Implementation plan

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

## Implementation Steps

The source does not provide a separate implementation steps section; no additional implementation steps is recorded.

## Proof

### Source: Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`

## Validation

The source does not provide a separate validation section; no additional validation is recorded.

## Stop Conditions

### Source: Non-goals

- No real collider cut-over yet.
- No runtime transport deletion yet.
- No baseline repin.

### Source: Rollback plan

- Remove only the new schema/validation contracts and preserve the architect
  reference plus blocked sequencing notes.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

The source does not provide a separate lessons learned section; no additional lessons learned is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: Problem

The current launcher model lacks the vocabulary needed for a truthful physical
carrier graph. It can describe walls, guide rails, sensors, and optional travel
routes, but not support/guard/receiver/handoff roles or an explicit
observation-spine proof layer.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Implementation Review

The source does not provide a separate implementation review section; no additional implementation review is recorded.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

The tagged `carriers[]` union (kinds support/guard/receiver/observation_spine/handoff_seam, compile roles physical/observation/terminal_seam, required `ownerWorld` and `donorSourceIds`) shipped in cfd44a6a5 in `G/table/tableDefinitionTypes.ts`, with the validator `G/table/compiler/assertValidLauncherCarrierGraph.ts` (unique tags, donor provenance, no cross-world donor-span ownership, connected acyclic spine graph, exactly one terminal handoff seam, seam continuity) and tests in `compilePinballTable.validation.spec-impl.ts`. Observation spines generate no colliders. Runtime transport still moves the ball along observation spines (`LauncherTravelRoute.ts:133-134,173-174`), which the task defers ("No runtime transport deletion yet"). The test-plan commands were not run offline. Criterion 2 is read as a statement about the authored and compiled contract; the task's non-goal defers runtime transport deletion, which TASK-SKRIPT-25-06-14 and the remaining tasks of ST-SKRIPT-33-01 cover.
