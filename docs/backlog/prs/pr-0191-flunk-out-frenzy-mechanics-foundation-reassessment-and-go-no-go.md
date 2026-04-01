---
type: pr
id: PR-0191
title: "Flunk-Out Frenzy: mechanics foundation reassessment and go/no-go"
status: done
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-25-05"
tags: ["frontend", "games", "architecture", "planning"]
dependencies:
  - "PR-0190"
acceptance_criteria:
  - "The post-tranche state of `PhysicsWorld`, `MachineEvent`, table-definition seams, and rule modules is reviewed against the ST-25-05 architecture goals before any physical-fidelity or advanced-device PR starts."
  - "The reassessment records whether the runtime, physics, and rules boundaries stayed within file-size and responsibility targets after `PR-0188` through `PR-0190`."
  - "The follow-on mechanics backlog is either confirmed as-is or explicitly resoped before `PR-0192` through `PR-0195` are allowed to proceed."
---

## Decision: GO (2026-04-01)

The reassessment of the foundation tranche (`PR-0188` through `PR-0190`) confirms
that the modular architecture for Flunk-Out Frenzy is stable, performant, and
correctly decoupled.

### Architectural findings:
- **Module Boundaries**: The separation between `PhysicsWorld` (Rapier),
  `RuleEngine` (pure state transitions), and `GameRuntime` (host integration) is
  strictly enforced.
- **File Sizes**: All critical modules remain under the 500 LOC target
  (`PhysicsWorld.ts` is at 426 LOC).
- **Event Surface**: The `MachineEvent` and `GameEffectEvent` vocabularies are
  rich enough to describe complex pinball mechanics without leaking
  implementation details.
- **Verification**: End-to-end live checks via the `__FOF_DEBUG__` interface
  confirmed that semantic events (e.g., target hits) correctly trigger complex
  rule outcomes (e.g., jackpot lit and awarded) and HUD updates.

The tranche-two physical-fidelity and advanced-device work (`PR-0192` through
`PR-0195`) is cleared to proceed as planned.

## Problem

The first mechanics tranche is intentionally about architecture as much as game
behavior. If `PR-0188` through `PR-0190` land but still leave oversized files,
unclear event semantics, or brittle runtime coupling, moving directly into
flipper fidelity and advanced devices would compound the problem instead of
building on a stable foundation.

## Goal

Insert a formal go or no-go checkpoint after the foundation tranche:

- review the post-tranche seams in physics, rules, engine, and table authoring
- confirm the next work should deepen fidelity rather than reopen architecture
- rescope follow-on PRs if the tranche exposes new risks

## Non-goals

- No new gameplay devices or rule features in this PR.
- No backend competition work.
- No visual shell redesign.

## Implementation plan

- Review the implemented state of:
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/PhysicsWorld.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/physicsTypes.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/rules/RuleEngine.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/engine/PrototypeAlphaGameEngine.ts`
  - `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTable.ts`
  - any new tranche-one helper modules
- Verify the event surface, module boundaries, and test coverage are stable
  enough for:
  - flipper-contact fidelity work
  - explicit launcher-state work
  - capture or eject devices
  - ramps, gates, and higher-level objectives
- Update `ST-25-05`, `EPIC-25`, and the follow-on PR docs if the tranche
  reveals that any downstream slice should be split, merged, or delayed.
- Record the explicit go or no-go decision and the reasons for it in the
  planning docs and `.agents/handoff.md`.

## Test plan

Automated:

- rerun the tranche-one test suites and any focused runtime or engine coverage
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`

Manual/live:

- play at least one local run in
  `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
  and confirm the tranche-one boundaries still support a clean, playable
  browser-local session

## Rollback plan

- No product rollback is required because this is a reassessment gate.
- If the review finds the foundation unstable, keep `PR-0192` through
  `PR-0195` blocked and update the planning docs instead of proceeding.
