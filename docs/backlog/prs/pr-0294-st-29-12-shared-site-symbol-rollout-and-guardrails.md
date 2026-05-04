---
type: pr
id: PR-0294
title: "ST-29-12: shared site symbol rollout and guardrails"
status: ready
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-12"
tags: ["frontend", "components", "design-system", "icons", "site-wide"]
dependencies:
  - "EPIC-29"
  - "PR-0292"
  - "PR-0293"
acceptance_criteria:
  - "Given common global actions render outside Klassrumskartan, when users see create, edit, delete, close, share/copy link, file/download, history, or configure affordances, then those symbols match the approved semantic matrix."
  - "Given a future developer searches for canonical symbol usage, when they read the reference or wrapper registry, then the intended wrapper and allowed semantic scope are discoverable."
  - "Given an icon remains direct-imported from Lucide, when the audit completes, then it has an explicit reason or belongs to an approved local leaf surface."
---

## Problem

Even if Klassrumskartan is corrected, the broader SPA can continue drifting if
common actions, file/vault semantics, editor controls, profile/catalog symbols,
and direct Lucide imports keep evolving separately.

## Goal

Roll out the approved global symbol decisions to the shared SPA surfaces and add
lightweight guardrails that keep future symbol usage explainable.

## Non-goals

- A full site redesign.
- New tooltip implementation; that remains under `ST-29-08`.
- Replacing every one-off icon if it is genuinely local and documented.

## Implementation Plan

1. Audit current direct `lucide-vue-next` imports outside Klassrumskartan.
2. Route approved global symbols through shared wrappers.
3. Leave local one-off icons only where the decision matrix explicitly allows a
   local leaf import.
4. Add a focused test or static assertion for the highest-risk prohibited
   overloads, especially link symbols outside link/share surfaces.
5. Update the symbol reference with any implementation notes needed by future
   agents.

## Test Plan

- `pdm run fe-type-check`
- `pdm run fe-lint`
- focused Vitest specs for touched shared components
- browser proof only for changed visible shared UI routes
- `git diff --check`

## Rollback Plan

Revert shared runtime changes while preserving the decision matrix and
Klassrumskartan-specific implementation if those remain valid.
