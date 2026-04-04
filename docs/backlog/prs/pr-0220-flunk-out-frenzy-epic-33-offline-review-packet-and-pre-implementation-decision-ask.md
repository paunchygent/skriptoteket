---
type: pr
id: PR-0220
title: "Flunk-Out Frenzy: EPIC-33 offline review packet and pre-implementation decision ask"
status: done
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-33-01"
tags: ["frontend", "games", "launcher", "physics", "planning", "architecture", "review", "repomix"]
dependencies:
  - "PR-0216"
  - "REV-EPIC-33"
  - "REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04"
acceptance_criteria:
  - "Given `EPIC-33` is now the approved prerequisite before any further physical cut-over continuation, when this task is complete, then the repo contains a new offline-review packet grounded in the approved epic, story, and planned PR sequence rather than in the earlier pre-approval planning state."
  - "Given the next implementation step is `PR-0217`, when this task is complete, then the offline reviewer is asked to assess the implementation order and advise on the exact pre-cut-over uncertainties that still need explicit decisions before code changes begin."
  - "Given the remaining uncertainties are architectural rather than cosmetic, when this task is complete, then the packet asks for explicit guidance on carrier schema shape, launcher-world ownership, donor-to-collider representation, Rapier stability policy, observer semantics, temporary correction policy, and future baseline-repin criteria."
  - "Given this is an external review/decision packet, when this task is complete, then a targeted repomix package, reviewer brief, context note, and exact file list exist under `.agents/repomix_packages/` and are validated against the current repo state."
  - "Given docs-as-code must remain the source of truth, when this task is complete, then `docs/index.md` and `.agents/handoff.md` reflect that `PR-0220` now sits ahead of `PR-0217` as the last planning/review checkpoint before implementation."
---

## Problem

`EPIC-33` is now approved, and the implementation order is clearer than it was
during the earlier architect packet in `PR-0216`. But the repo still has
several critical pre-cut-over decisions that are not fully pinned:

- carrier schema shape in `PR-0217`
- exact launcher-world ownership boundary
- donor-to-collider representation strategy
- Rapier contact / stability policy
- observer semantics for `PR-0219`
- temporary correction policy during bring-up
- future baseline-repin trigger after the foundation phase

Those are not implementation details we should improvise while coding. They are
the last decision-grade uncertainties that can still distort the foundation
lane if left vague.

## Goal

Create a second offline review packet that reflects the approved `EPIC-33`
planning stack and asks the offline reviewer for explicit guidance on the
remaining pre-implementation uncertainties.

This slice should:

1. package the new docs-as-code state (`REV-EPIC-33`, `EPIC-33`, `ST-33-01`,
   `PR-0217` through `PR-0219`)
2. explain the current recommended implementation order
3. ask the offline reviewer to critique that order if needed
4. request decision-grade advice on the exact unresolved architecture and
   verification questions that must be settled before `PR-0217` starts

## Non-goals

- No implementation of `PR-0217`, `PR-0218`, or `PR-0219`.
- No runtime behavior changes.
- No weakening of `PR-0214`.
- No baseline repin.
- No replacement of the approved architect reference; this packet is a follow-on
  review request grounded in that reference.

## Implementation plan

### Checkpoint A. Frame the new offline-review ask

1. Create a new backlog PR task that explicitly states this packet is a
   post-`REV-EPIC-33` pre-implementation decision lane.
2. Position it ahead of `PR-0217` in `ST-33-01` so the order is visible in the
   docs, not only in session chat.

### Checkpoint B. Build the new reviewer brief and context note

1. Create a concise reviewer brief that:
   - summarizes the approved `EPIC-33` lane
   - lists the current recommended implementation order
   - asks the reviewer to assess whether that order is correct
   - asks for explicit recommendations on the unresolved decisions
2. Create a compact context note that:
   - summarizes what `REV-EPIC-33` settled
   - summarizes what is still intentionally unsettled
   - explains why each open question matters for correctness

### Checkpoint C. Build the repomix package

1. Create a targeted file list covering:
   - the approved architect reference
   - `REV-EPIC-33`, `EPIC-33`, `ST-33-01`
   - `PR-0215`, `PR-0216`, `PR-0217`, `PR-0218`, `PR-0219`, and this task
   - the core launcher/compiler/runtime files implicated by the open questions
   - the `PR-0214` truth-surface docs/tooling plus the current trace summary
2. Generate a new `.xml` repomix package under `.agents/repomix_packages/`.

### Checkpoint D. Route the outcome into the implementation order

1. Keep `PR-0217` as the expected first implementation slice.
2. Treat the offline review output as the last decision checkpoint before
   `PR-0217` begins.
3. Do not start implementation if the review changes the ordering or reveals
   a new blocker in the ownership/modeling assumptions.

## Test plan

- `pdm run docs-validate`
- `repomix --style xml --no-gitignore --output .agents/repomix_packages/repomix-flunk-out-frenzy-epic-33-foundation-review.xml --include "<targeted file list>"`

## Rollback plan

This slice is packaging and planning only.

If the framing proves wrong:

1. keep `EPIC-33` / `ST-33-01` active
2. supersede `PR-0220` with a corrected reviewer packet task
3. rebuild the package against the corrected implementation order instead of
   guessing during code changes

## Closure note

The offline reviewer has now answered the decision questions this packet was
created to ask, and the resulting guidance has been folded back into
`PR-0217`, `PR-0218`, and `PR-0219`.

`PR-0220` is therefore complete as a planning/review lane and no longer blocks
the start of `PR-0217`.
