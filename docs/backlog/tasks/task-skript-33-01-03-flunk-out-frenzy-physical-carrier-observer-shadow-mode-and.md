---
type: task
id: TASK-SKRIPT-33-01-03
title: 'Flunk-Out Frenzy: physical carrier observer shadow mode and cut-over readiness
  gate'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-33-01
task_kind: story
acceptance_criteria:
- Given the physical carrier cut-over must not happen on intuition alone, when this
  task is complete, then the runtime can shadow carrier occupancy/progress against
  the current transport model and expose divergence evidence without using the observer
  to fake green results.
- Given route phases must be earned by physical evidence, when this task is complete,
  then a `route_*` phase is valid only when raw trace rows show launcher ownership
  plus physical occupancy evidence on compiled carrier/receiver geometry, after which
  progress may be projected onto the matched observation spine.
- Given `PR-0219` must prove more than generic divergence, when this task is complete,
  then the raw trace includes occupied carrier/receiver tags, active observation-spine
  tag, projected progress, and correction counters/details in addition to the current
  route/seam/handoff facts.
- Given temporary seam correction may exist during bring-up, when this task is complete,
  then correction counters and intervention telemetry are explicit, any correction
  is treated as blocked debt, and production readiness still requires the counter
  to reach `0`.
- Given `PR-0214` remains the truth surface, when this task is complete, then no drift
  threshold widening or baseline repin is introduced; instead the repo gains an explicit
  go/no-go gate for later transport deletion with hard blockers for non-raw-row-backed
  summary claims, route phases without physical occupancy evidence, projected-progress
  discontinuities without seam evidence, or observer/transport disagreement beyond
  declared thresholds.
---

## Context


The physical carrier model needs a proof-first shadow phase before route-driven
transport can be deleted safely.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Story Contract Slice


Create the observer shadow mode and cut-over readiness gate that must pass
before physical carrier cut-over work resumes.

## Contract Inputs

No separate contract inputs is stated in the source.

## Plan


- Shadow physical carrier occupancy/progress against current transport-driven
  output.
- Define a minimal truthful observer contract:
  - launcher ownership plus physical occupancy evidence gates phase validity
  - observation spines classify/provide progress only after occupancy is proven
  - summary claims stay raw-row-backed rather than reconstructed
- Extend the raw trace schema with the carrier-observer facts needed to prove
  shadow behavior:
  - occupied carrier/receiver tags
  - active observation-spine tag
  - projected progress
  - correction counters/details
- Emit divergence evidence and seam-correction counters explicitly.
- Extend the `PR-0214` decision surface with the cut-over readiness facts needed
  for a future go/no-go, including hard blockers for:
  - any `route_*` phase without physical occupancy evidence
  - projected-progress discontinuity without a seam transition
  - observer/transport disagreement on first occupancy, endpoint bridge,
    descent, or handoff beyond declared thresholds
  - any non-zero production correction count

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_parity_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`

## Validation

No separate validation is stated in the source.

## Stop Conditions


- Remove only the shadow-observer/cut-over-readiness additions and keep the
  stricter sequencing and architect-grounded contracts intact.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Non-goals


- No transport deletion yet.
- No physical baseline repin yet.
- No gameplay-readiness claim beyond observer/governance proof.

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Implementation Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
