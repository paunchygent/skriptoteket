---
type: pr
id: PR-0204
title: "Flunk-Out Frenzy: ruthless independent review gate for launcher input and overlay seam"
status: ready
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-06"
tags: ["frontend", "games", "physics", "launcher", "ux", "input", "review-gate"]
dependencies:
  - "PR-0200"
  - "PR-0201"
  - "PR-0202"
  - "PR-0203"
acceptance_criteria:
  - "Given this is an independent gate, when this task is complete, then the reviewer is explicitly different from the plan/implementation author, review delegation is disallowed for this gate, and self-approval is invalid."
  - "Given current authoritative live browser truth reports that the plunger does not move and has no visible launch effect, when this task is complete, then `approved` is forbidden unless fresh live evidence overturns that finding by proving all of: visible plunger pullback/release, visible ball response from that release, and `gate-passed` semantics from real `sw16` exit; otherwise the only valid verdict is `changes_requested`."
  - "Given architect invariants are hard requirements, when this task is complete, then the review explicitly checks and preserves: seam continuity `xy<=1/z<=1`, no helper rails/freehand seam geometry, terminal-route-only `handoffVelocity` semantics, and real `sw16`-exit gate semantics."
  - "Given launcher UX/input is the current risk, when this task is complete, then review coverage explicitly proves that no gameplay overlay/HUD/settings layer intercepts launcher pullback/release in active play, and that keyboard plus pointer launch paths are checked under real focus states with overlays closed and reopened."
  - "Given ruthless-review quality requirements, when this task is complete, then findings are severity-ordered with file references, exact fixes, and proof requirements; summary-only sign-off is invalid."
  - "Given this gate must remain auditable, when this task is complete, then the final verdict is recorded in a retained repo review artifact with reviewer identity and evidence links, not only in ad hoc session notes."
---

## Problem

The launcher seam architecture and compile/runtime contracts were tightened, but
live user verification reports that the plunger still does not move or visibly
affect the ball in gameplay. This is exactly the type of mismatch that can pass
narrow deterministic tests while failing real UX/input behavior.

## Goal

Create an explicit independent ruthless-review gate for the launcher
input/overlay plan and current seam behavior so implementation cannot proceed on
assumptions. The reviewer must either approve with evidence or block with
actionable findings.

## Required review scope (files/contracts)

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/input/KeyboardInputController.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/GameHost.vue`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaVpwDonorMap.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/tableDefinitionTypes.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`

## Non-goals

- No scope expansion to whole-table architecture changes.
- No tolerance relaxation (`xy<=1/z<=1` stays strict).
- No helper rails, no freehand seam geometry, no synthetic gate-start events.

## Implementation plan

- Prepare the review package for `PR-0200` launcher closure and current
  UX/input seam behavior, including:
  - exact file scope listed above
  - authored route chain (`overhead -> endpoint-bridge -> descent`)
  - compiler seam contracts and terminal-route-only `handoffVelocity` semantics
  - launcher runtime ownership/release path
  - overlay/focus/input interaction seams for keyboard and pointer paths
  - latest browser/live findings and artifacts
- Run an independent ruthless review pass focused on:
  - input capture and interaction layering (keyboard/pointer/focus paths)
  - visible plunger motion and launch effect in live runtime
  - preservation of architect invariants and donor semantics
- Record findings as severity-ordered, file-referenced actions with required
  verification commands.
- Require explicit sign-off outcome:
  - `approved` only after fresh live proof overturns the current authoritative
    plunger defect
  - `changes_requested` for any unresolved seam/UX contradiction
- Record the verdict in
  `docs/backlog/reviews/review-epic-25-competitive-games-and-flunk-out-frenzy.md`
  under a dedicated `PR-0204` supplemental section with reviewer identity,
  verdict, and evidence links.

## Test plan

- `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec.ts src/components/apps/flunk-out-frenzy/game/physics/plungerLaneState.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.flippers.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.captureDevices.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.collisions.spec.ts src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_flunk_out_frenzy_route_check --base-url http://127.0.0.1:5173`
- launcher behavior proof must include either:
  - a dedicated launcher proof command that emits plunger/ball/exit evidence, or
  - a manual launcher matrix with retained artifacts proving pullback/release
    visibility, ball response, keyboard + pointer launch paths, overlay-open
    and overlay-closed behavior, and `sw16`-exit semantics.
- required retained artifacts for gate sign-off:
  - `.artifacts/flunk-out-frenzy-live-launch-matrix/launch-matrix-summary.json`
  - `.artifacts/flunk-out-frenzy-live-launch-matrix/launch-matrix-after.png`

## Rollback plan

- If the review gate is dropped, do not merge launcher-seam closure changes as
  “accepted”; revert task status to pending and keep implementation blocked
  until independent sign-off is restored.
