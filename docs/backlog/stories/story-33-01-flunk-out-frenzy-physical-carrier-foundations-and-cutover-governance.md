---
type: story
id: ST-33-01
title: "Flunk-Out Frenzy physical carrier foundations and cut-over governance"
status: ready
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
epic: "EPIC-33"
dependencies:
  - "ST-25-06"
  - "PR-0216"
  - "REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04"
acceptance_criteria:
  - "Given the architect direction now defines a physical carrier graph plus observation-spine overlay as the target model, when this story is complete, then the launcher/table authored schema distinguishes support, guard, receiver, observation-spine, and handoff-seam roles without overloading `guideRails` or `travelRoutes`."
  - "Given world ownership is the critical architectural risk, when this story is complete, then the compiler and launcher-world geometry plan make it explicit which causal elevated-route surfaces live in the launcher Rapier world and where the one terminal board handoff seam occurs."
  - "Given physical cut-over work must not outrun its foundations, when this story is complete, then a shadow-observer and cut-over readiness gate exist so future transport deletion can be judged against strict proof rather than intuition."
  - "Given `PR-0214` is the canonical truth surface, when this story is complete, then no drift thresholds are widened, no summary reconstruction is introduced, and no baseline repin is allowed yet."
  - "Given existing cut-over tasks were planned under route-driven assumptions, when this story is complete, then those tasks are explicitly blocked or re-scoped so no slotted work remains in conflict with the architect reference."
ui_impact: "No direct user-facing change; this is architecture and contract groundwork for later physical cut-over."
data_impact: "No durable backend data impact; frontend authored/compiler/runtime contracts only."
---

## Context

The architect direction in
`docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`
made one thing explicit: the current route-driven launcher transport cannot be
incrementally turned into a truthful physical rail by runtime tweaks alone.

The underpinnings are missing:

- carrier-role schema
- launcher-world ownership rules
- donor-backed carrier compiler output
- observation-spine proof separated from motion
- cut-over readiness governance

Without those foundations, further physical cut-over work would risk papering
over critical limitations in the current physics and modeling world.

## What this story is really about

- establish physical carrier semantics before physical carrier cut-over
- keep proof stricter than before, not softer
- make `travelRoutes` a proof/observation contract rather than a transport
  contract
- prevent `PR-0200`, `PR-0202`, and `PR-0203` from continuing under stale
  route-driven assumptions

## Planned PR slices

1. [PR-0220: Flunk-Out Frenzy EPIC-33 offline review packet and pre-implementation decision ask](../prs/pr-0220-flunk-out-frenzy-epic-33-offline-review-packet-and-pre-implementation-decision-ask.md)
2. [PR-0217: Flunk-Out Frenzy carrier-role schema, observation-spine contract, and launcher-world ownership rules](../prs/pr-0217-flunk-out-frenzy-carrier-role-schema-observation-spine-contract-and-launcher-world-ownership-rules.md)
3. [PR-0218: Flunk-Out Frenzy launcher-world carrier compiler and donor overhead collider foundation](../prs/pr-0218-flunk-out-frenzy-launcher-world-carrier-compiler-and-donor-overhead-collider-foundation.md)
4. [PR-0219: Flunk-Out Frenzy physical carrier observer shadow mode and cut-over readiness gate](../prs/pr-0219-flunk-out-frenzy-physical-carrier-observer-shadow-mode-and-cutover-readiness-gate.md)

Dependency chain: `PR-0220 -> PR-0217 -> PR-0218 -> PR-0219`

Only after this story is complete may the physical cut-over tasks resume.

## Execution strategy

- `PR-0220` asks the offline reviewer to assess the approved implementation
  order and advise on the remaining pre-implementation uncertainties.
- `PR-0217` defines the model.
- `PR-0218` compiles/builds the model into launcher-world carrier surfaces.
- `PR-0219` proves the observer/governance layer needed before transport
  deletion.
- Existing cut-over tasks remain blocked until this story is complete.

## Non-goals

- No final physical carrier cut-over yet.
- No baseline repin.
- No deletion of route-driven transport in this story.
- No broad whole-table carrier migration beyond what is needed to define the
  launcher/elevated-route foundation.
