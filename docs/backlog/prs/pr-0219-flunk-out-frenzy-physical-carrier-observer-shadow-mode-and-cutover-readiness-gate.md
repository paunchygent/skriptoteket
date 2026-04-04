---
type: pr
id: PR-0219
title: "Flunk-Out Frenzy: physical carrier observer shadow mode and cut-over readiness gate"
status: ready
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-33-01"
tags: ["frontend", "games", "launcher", "physics", "proof-first", "telemetry", "readiness"]
dependencies:
  - "PR-0218"
  - "PR-0214"
  - "REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04"
acceptance_criteria:
  - "Given the physical carrier cut-over must not happen on intuition alone, when this task is complete, then the runtime can shadow carrier occupancy/progress against the current transport model and expose divergence evidence without using the observer to fake green results."
  - "Given temporary seam correction may exist during bring-up, when this task is complete, then correction counters and intervention telemetry are explicit and production acceptance still requires them to reach `0`."
  - "Given `PR-0214` remains the truth surface, when this task is complete, then no drift threshold widening or baseline repin is introduced; instead the repo gains an explicit go/no-go gate for later transport deletion."
---

## Problem

The physical carrier model needs a proof-first shadow phase before route-driven
transport can be deleted safely.

## Goal

Create the observer shadow mode and cut-over readiness gate that must pass
before physical carrier cut-over work resumes.

## Non-goals

- No transport deletion yet.
- No physical baseline repin yet.
- No gameplay-readiness claim beyond observer/governance proof.

## Implementation plan

- Shadow physical carrier occupancy/progress against current transport-driven
  output.
- Emit divergence evidence and seam-correction counters explicitly.
- Extend the `PR-0214` decision surface with the cut-over readiness facts needed
  for a future go/no-go.

## Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_parity_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`

## Rollback plan

- Remove only the shadow-observer/cut-over-readiness additions and keep the
  stricter sequencing and architect-grounded contracts intact.
