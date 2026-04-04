---
type: pr
id: PR-0213
title: "Flunk-Out Frenzy: live trace contract parity remediation"
status: done
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "telemetry", "playwright", "proof-first", "trace-contract", "parity"]
dependencies:
  - "PR-0209"
  - "PR-0212"
acceptance_criteria:
  - "Given the live Playwright artifact currently reconstructs proof state beyond what raw rows show, when this task is complete, then the live artifact reports only directly observed per-step seam truth or labels any derived summary field as derived rather than direct evidence."
  - "Given `PR-0209` requires per-step phase and seam visibility, when this task is complete, then qualifying live cases no longer claim `route_endpoint_bridge`, `handoff_to_board`, or `board_drop_preimpact` solely through post-hoc insertion when the raw live rows do not expose those steps."
  - "Given focused and live artifacts are currently not contract-equivalent, when this task is complete, then they either share one explicit row/summary contract (field names, cadence semantics, seam markers) or `PR-0209` plus downstream docs are narrowed so the live contract is intentionally weaker and cannot be misread as parity."
  - "Given this slice owns only proof-surface mismatch, when this task is complete, then no launcher geometry changes, no release-speed tuning, no route-transport behavior changes, and no new gameplay heuristics are introduced."
  - "Given reviewability depends on retained evidence, when this task is complete, then `.agents/handoff.md` records the exact focused and live commands, artifact paths, and a short note explaining whether parity was achieved or the live contract was explicitly narrowed."
---

## Problem

`PR-0212` closed the audit gate by making the current truth gap explicit: the
focused runtime artifact and the live Playwright artifact are not presently the
same proof surface. The focused artifact exposes direct `route_endpoint_bridge`
and `seam_transition` evidence with the expected snake_case `dt_ms=16`
contract, while the live artifact currently uses a translated shape, a
different sampled cadence, and summary reconstruction that can overstate raw
per-step seam truth.

That mismatch is now documented, but it is still unresolved. As long as the
live artifact can look PR-0209-complete without actually carrying equivalent raw
trace truth, reviewers can still get a false-green signal from the live proof
surface.

## Goal

Remediate the live trace proof-surface mismatch so the live Playwright artifact
has an honest, bounded contract:

1. either full parity with the focused artifact for the fields that matter to
   seam truth, or
2. an explicitly narrowed live contract that no longer pretends to prove more
   than it actually does.

## Non-goals

- No launcher speed or charge-behavior tuning.
- No donor geometry or route-path edits.
- No seam tolerance relaxation (`xy<=1`, `z<=1` stays strict).
- No changes to route transport mechanics beyond what is strictly required to
  expose truthful telemetry.
- No reopening of the broader shortcut-remediation slice from `PR-0212`.
- No contract narrowing or live-contract downgrade inside this PR.

## Scope lock (bounded)

Primary implementation scope:

- `scripts/playwright_flunk_out_frenzy_launch_trace_check.py`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/world/PhysicsWorldTrace.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/test-support/physicsTestTelemetry.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.proof.spec-impl.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/GameRuntime.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/core/runtimeTypes.ts`

Proof/contract scope:

- `docs/backlog/prs/pr-0209-flunk-out-frenzy-end-to-end-launch-to-drop-telemetry-contract.md`
- `docs/backlog/prs/pr-0212-flunk-out-frenzy-launcher-shortcut-breach-inventory-and-truth-gate-audit.md`
- `.agents/handoff.md`

Out of scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcher/LauncherTravelRoute.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.ts`

## Contract decision surface

This slice starts by attempting full parity only. If that attempt proves parity
is blocked without crossing this PR's scope boundary, the implementation must
stop, record the blocker, and route any contract narrowing into a separate
follow-up PR. That follow-up may only start after this PR is closed as done with
reservations.

For planning clarity, the possible end states are:

### Option A. Full live/focused parity

- Live and focused artifacts use the same field naming convention.
- Live and focused artifacts use one declared `dt_ms` / cadence contract.
- Qualifying live traces expose raw per-step `route_endpoint_bridge`,
  `seam_transition`, `handoff_to_board`, and board-drop markers directly.
- Summary fields are derived only from raw evidence that is actually present in
  the live rows.

### Option B. Explicitly narrowed live contract

- `PR-0209` and the live Playwright script are updated so the live artifact is
  clearly documented as a weaker proof surface than the focused artifact.
- Any summary field that is derived rather than directly observed is named or
  annotated as derived.
- Reviewers can no longer mistake the live artifact for full per-step seam
  parity with the focused runtime artifact.

Option B is explicitly out of scope for direct implementation in this PR. It is
listed here only to define the fallback path that requires a separate PR after
this slice is closed as done with reservations.

## Required remediation rules

1. No hidden reconstruction:
   - Do not insert `route_endpoint_bridge`, `handoff_to_board`, or
     `board_drop_preimpact` into a live summary as if they were directly
     observed if the raw live rows do not expose those steps.
2. No silent schema drift:
   - If live and focused artifacts differ in key naming or cadence semantics,
     that difference must be intentional, documented, and reflected in tests and
     docs.
3. No consumer ambiguity:
   - Downstream docs must make it obvious which fields are direct evidence and
     which are derived summaries.
4. No gameplay scope creep:
   - If parity cannot be achieved without changing launcher behavior, stop and
     keep that work for the later shortcut-remediation slice instead of
     stretching this PR.
5. No in-slice downgrade:
   - If direct observation remains blocked, do not narrow the contract here.
     Instead, document the blocker, mark this slice done with reservations, and
     open a separate PR for any proposed live-contract weakening.

## Implementation plan

1. Attempt Option A only:
   - move live and focused artifact shaping toward one shared serialization
     contract
   - expose direct per-step seam truth in the live artifact if it can be done
     within this slice's proof-surface boundary
2. Remove the current false-green path:
   - stop treating inserted `route_endpoint_bridge`,
     `handoff_to_board`, and `board_drop_preimpact` as raw live proof when
     they are not present in raw rows
3. Lock the contract in tests:
   - focused proof tests assert the focused artifact shape
   - live proof checks assert direct parity fields rather than inferred summary
     upgrades
4. If parity is blocked, stop and document the blocker:
   - record why direct observation is blocked
   - record which field/claim cannot be made truthful in this slice
   - record what separate follow-up PR is required for any contract narrowing
5. Update docs and handoff evidence:
   - refresh `PR-0209` only if parity is achieved in this slice
   - record exact commands, artifact paths, and parity outcome in
     `.agents/handoff.md`

## Test plan

- Focused verification:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.proof.spec-impl.ts`
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts`
- Contract verification:
  - inspect focused artifact rows for direct `route_endpoint_bridge` and
    non-null `seam_transition`
  - inspect live artifact rows for whether the same direct evidence now exists
  - if it does not, stop the slice rather than weakening the contract here
- Live verification:
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`
- Quality gates:
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run docs-validate`

## Rollback plan

- If the parity/narrowing decision proves wrong, roll back only the artifact
  contract and doc changes from this slice.
- Do not use rollback as justification to restore the ambiguous current state
  where live summaries can be mistaken for full per-step seam proof.
- Any needed gameplay or launcher-behavior changes discovered during this work
  must move to the later runtime shortcut-remediation PR rather than being
  patched into this slice.
- Any live-contract narrowing discovered during this work must also move to a
  separate follow-up PR after this slice is closed as done with reservations.
