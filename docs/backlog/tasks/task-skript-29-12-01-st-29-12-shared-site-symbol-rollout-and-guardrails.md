---
type: task
id: TASK-SKRIPT-29-12-01
title: 'ST-29-12: shared site symbol rollout and guardrails'
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
story: ST-SKRIPT-29-12
task_kind: story
acceptance_criteria:
- Given common global actions render outside Klassrumskartan, when users see create,
  edit, delete, close, share/copy link, file/download, history, or configure affordances,
  then those symbols match the approved semantic matrix.
- Given a future developer searches for canonical symbol usage, when they read the
  reference or wrapper registry, then the intended wrapper and allowed semantic scope
  are discoverable.
- Given an icon remains direct-imported from Lucide, when the audit completes, then
  it has an explicit reason or belongs to an approved local leaf surface.
---

## Context

Source: `docs/backlog/prs/pr-0294-st-29-12-shared-site-symbol-rollout-and-guardrails.md`. ST-29-12: shared site symbol rollout and guardrails.

Even if Klassrumskartan is corrected, the broader SPA can continue drifting if common actions, file/vault semantics, editor controls, profile/catalog symbols, and direct Lucide imports keep evolving separately. Roll out the approved global symbol decisions to the shared SPA surfaces and add lightweight guardrails that keep future symbol usage explainable. - A full site redesign. - New tooltip implementation; that remains under `ST-29-08`. - Replacing every one-off icon if it is genuinely local and documented. 1. Audit current direct `lucide-vue-next` imports outside Klassrumskartan. 2. Route approved global symbols through shared wrappers. 3. Leave local one-off icons only where the decision

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-29-12-01 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

Even if Klassrumskartan is corrected, the broader SPA can continue drifting if
common actions, file/vault semantics, editor controls, profile/catalog symbols,
and direct Lucide imports keep evolving separately.

### Goal

Roll out the approved global symbol decisions to the shared SPA surfaces and add
lightweight guardrails that keep future symbol usage explainable.

### Non-goals

- A full site redesign.
- New tooltip implementation; that remains under `ST-29-08`.
- Replacing every one-off icon if it is genuinely local and documented.

### Implementation Plan

1. Audit current direct `lucide-vue-next` imports outside Klassrumskartan.
2. Route approved global symbols through shared wrappers.
3. Leave local one-off icons only where the decision matrix explicitly allows a
   local leaf import.
4. Add a focused test or static assertion for the highest-risk prohibited
   overloads, especially link symbols outside link/share surfaces.
5. Update the symbol reference with any implementation notes needed by future
   agents.

### Test Plan

- `pdm run fe-type-check`
- `pdm run fe-lint`
- focused Vitest specs for touched shared components
- browser proof only for changed visible shared UI routes
- `git diff --check`

### Rollback Plan

Revert shared runtime changes while preserving the decision matrix and
Klassrumskartan-specific implementation if those remain valid.

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
