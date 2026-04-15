---
type: pr
id: PR-0165
title: "ST-30-01: transition continuity decision, inventory, and adoption plan"
status: done
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-30-01"
tags: ["docs", "frontend", "ux", "transitions", "planner", "editor"]
dependencies:
  - "ADR-0077"
  - "EPIC-30"
  - "ST-29-02"
acceptance_criteria:
  - "Given the planner continuity fix is now the known-good baseline, when this PR lands, then the repo contains a dedicated ADR and reference that make the retained-surface overlap crossfade the canonical same-shell selector transition pattern."
  - "Given future adoption needs scoping, when this PR lands, then the repo contains an explicit inventory of qualifying same-shell selector and rail transitions with priorities and owning files."
  - "Given future implementation should be discoverable from frontend docs, when this PR lands, then the relevant design-system references and docs index point to the new continuity artifacts."
  - "Given this slice is planning-only, when this PR lands, then it changes no product logic and verification is satisfied by docs validation."
---

## Problem

The planner fix solved a real transition bug, but right now that knowledge lives mostly in the
implementation itself. Without a shared decision and inventory, the editor and other selector-driven
surfaces can still ship a different, visibly worse handoff model.

## Goal

Turn the planner continuity fix into:

- one explicit architecture/design decision
- one reusable frontend reference pattern
- one cross-app adoption epic
- one first-story inventory and rollout plan

## Non-goals

- Implementing the editor cutover in this PR
- Reworking route-level page transitions
- Auditing every single animation in the SPA

## Implementation plan

1. Add an ADR for same-shell selector continuity.
2. Add a frontend reference that explains the pattern and inventories adoption targets.
3. Create a cross-app epic plus first story for phased rollout.
4. Create the first PR task doc for the planning/inventory slice.
5. Update the frontend design-system references and `docs/index.md` so the new rule is easy to
   find.
6. Update `.codex/handoff.md` because the backlog surface changes in this session.

## Test plan

- `pdm run docs-validate`

## Rollback plan

- Revert the docs package together if the naming or scoping is rejected in review.
- Keep the planner implementation itself; this PR only governs the future adoption workflow.

## References

- Story parent: [ST-30-01](../stories/story-30-01-frontend-transition-continuity-inventory-and-canonical-adoption-plan.md)
- Epic parent: [EPIC-30](../epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md)
- Transition ADR: [ADR-0077](../../adr/adr-0077-same-shell-transition-continuity.md)
- Transition reference: [REF-frontend-transition-continuity-v1](../../reference/ref-frontend-transition-continuity-v1.md)
