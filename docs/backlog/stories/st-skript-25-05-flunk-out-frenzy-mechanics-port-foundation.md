---
type: story
id: ST-SKRIPT-25-05
title: Flunk-Out Frenzy mechanics-port foundation
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
epic: EPIC-SKRIPT-25
links:
  decisions:
  - ADR-SKRIPT-0073
acceptance_criteria:
- Given the local runtime needs richer table behavior, when this story is complete,
  then the physics boundary can emit semantic events for targets, lanes, capture/eject
  devices, ramps, gates, and launcher/feed lifecycle without leaking Rapier internals.
- Given the rule engine must grow beyond bumper and `L-A-T-E` rollover scoring, when
  this story is complete, then score, bonus, jackpot, ball-save or shoot-again, and
  objective progression are decomposed into small rule modules instead of one monolithic
  controller.
- Given the prototype-alpha table expands, when new devices are authored, then their
  geometry, tags, and authored parameters remain in typed TypeScript table modules
  rather than an external JSON content system.
- Given lightweight score submission and leaderboard support still matter later, when
  these mechanics slices land, then the browser-owned runtime plus the app/version/ruleset
  seams from `ST-25-02` remain intact and ready for a compact post-run score handoff.
- Given the work is reviewed incrementally, when the mechanics backlog is executed,
  then each PR remains narrow, testable, and aligned with the repo size budget instead
  of introducing a new engine monolith.
- Given repo file size limits are enforced, when PR-0210 completes, then all Flunk-Out
  Frenzy frontend modules are under 500 LoC with clear component communication patterns
  and no memory leaks.
retired_ids:
- ST-25-05
---

## Context

### Source: Context

`ST-25-02` proved that Flunk-Out Frenzy can run as a browser-owned local game
inside Skriptoteket, but its current mechanics surface is intentionally narrow:
bumper, sling, rollover, drain, simple launcher, and a single multiplier loop.
That is enough for a vertical slice, but not enough for the richer device and
rules semantics we want from a real pinball-like curated app.

This story uses the local clone of `SpaceCadetPinball` under
`.artifacts/SpaceCadetPinball/` as a behavioral donor for device semantics,
lane progression, bonus and jackpot loops, and ball-lifecycle choreography. It
does **not** copy that codebase wholesale. SDL rendering, native broadphase
code, and the monolithic `control.cpp` architecture remain out of scope.

## Epic Contract Slice

### Source: What this story is really about

- Broaden the event vocabulary between Rapier-backed physics and the pure
  rules layer.
- Refactor oversized gameplay files before adding more devices and rules.
- Add typed table-authoring seams for targets, capture devices, ramps, gates,
  and launcher or feed zones.
- Keep the runtime compatible with future `ST-SKRIPT-25-03` and `ST-SKRIPT-25-04`
  competition work instead of creating a local-only dead end.

## ADR Coverage

The source does not record separate ADR coverage.

## Contract Inputs

The source does not record separate contract inputs.

## Live Verification Plan

### Source: Planned PR slices

### Tranche 1: Foundation gate

1. [PR-0188: Flunk-Out Frenzy: machine-event contract expansion and PhysicsWorld decomposition](../prs/pr-0188-flunk-out-frenzy-machine-event-contract-expansion-and-physicsworld-decomposition.md)
2. [PR-0189: Flunk-Out Frenzy: lanes, targets, and tripwire devices](../prs/pr-0189-flunk-out-frenzy-lanes-targets-and-tripwire-devices.md)
3. [TASK-SKRIPT-25-05-01: Flunk-Out Frenzy: bonus, jackpot, and ball-lifecycle rule state](../tasks/task-skript-25-05-01-flunk-out-frenzy-bonus-jackpot-and-ball-lifecycle-rule-state.md)

### Formal reassessment gate

4. [PR-0191: Flunk-Out Frenzy: mechanics foundation reassessment and go/no-go](../prs/pr-0191-flunk-out-frenzy-mechanics-foundation-reassessment-and-go-no-go.md)

### Tranche 2: Higher-risk mechanics

5. [TASK-SKRIPT-25-05-02: Flunk-Out Frenzy: flipper contact model and explicit launcher state](../tasks/task-skript-25-05-02-flunk-out-frenzy-flipper-contact-model-and-explicit-launcher-state.md)
6. [TASK-SKRIPT-25-05-03: Flunk-Out Frenzy: capture, eject, and save devices](../tasks/task-skript-25-05-03-flunk-out-frenzy-capture-eject-and-save-devices.md)
7. [TASK-SKRIPT-25-05-04: Flunk-Out Frenzy: ramps, gates, and field-zone semantics](../tasks/task-skript-25-05-04-flunk-out-frenzy-ramps-gates-and-field-zone-semantics.md)
8. [TASK-SKRIPT-25-05-05: Flunk-Out Frenzy: objective controllers and bank progression](../tasks/task-skript-25-05-05-flunk-out-frenzy-objective-controllers-and-bank-progression.md)

### Tranche 3: Code quality and file size compliance

9. [TASK-SKRIPT-25-05-06: Flunk-Out Frenzy: file size compliance and frontend module decomposition](../tasks/task-skript-25-05-06-flunk-out-frenzy-file-size-compliance-and-frontend-module-decomposition.md)

Dependency chain: `PR-0188 -> PR-0189 -> TASK-SKRIPT-25-05-01 -> PR-0191 -> TASK-SKRIPT-25-05-02 ->
TASK-SKRIPT-25-05-03 -> TASK-SKRIPT-25-05-04 -> TASK-SKRIPT-25-05-05`. `TASK-SKRIPT-25-05-06` can proceed in parallel with Tranche 2
but must complete before any additional mechanics work that would further
increase file sizes.

## Non-Goals

### Source: Non-goals

- Reimplement the original Space Cadet engine or asset pipeline.
- Port `TEdgeManager`, SDL rendering, or native loader code.
- Introduce backend competition or leaderboard work in this story.
- Replace the browser-owned runtime with a native or emulated engine core.
- Externalize table content to JSON or add a general-purpose table editor.

## Notes

### Source: Execution strategy

- `PR-0188` through `TASK-SKRIPT-25-05-01` are one gated foundation tranche.
- `PR-0191` is mandatory before any physical-fidelity or advanced-device work
  starts.
- `TASK-SKRIPT-25-05-02` through `TASK-SKRIPT-25-05-05` stay blocked until the reassessment explicitly
  confirms the tranche-one seams are stable enough to deepen mechanics.

### Source: Notes

- Port semantics, not implementation details: preserve Rapier, Pixi, Howler,
  and the existing browser-owned runtime shell.
- Keep files under the repo size budget by splitting device factories and rule
  controllers before the new mechanics land.
- Treat the donor repo as a design reference for targets, lanes, capture,
  launcher, and drain behavior, not as a source tree to transliterate.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan Document Review

The source does not include a plan document review record.

## Story Closeout Review

The source does not include a story closeout review record.
