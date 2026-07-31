---
type: story
id: ST-SKRIPT-06-16
title: Backend SRP refactor of god modules
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
epic: EPIC-SKRIPT-06
acceptance_criteria:
- Targeted backend modules are split into smaller units (generally <=400–500 LOC)
  with clear single responsibilities.
- 'DDD/Clean boundaries are preserved: domain stays pure, web stays thin, infra implements
  protocols.'
- Protocol-first DI remains intact; repositories still avoid committing and UoW owns
  transactions.
- Existing behavior is preserved and covered by updated/added tests.
- Docs and module entrypoints are updated to reflect the new structure.
retired_ids:
- ST-06-16
---

## Context

Source: `docs/backlog/stories/story-06-16-backend-srp-refactor-god-modules.md`. Backend SRP refactor of god modules.

Several backend modules have grown into large, multi-responsibility files that are harder to reason about and test. We need a clean refactor pass that prioritizes clarity and SRP over minimizing churn. - This is a refactor story: no feature behavior changes. - Prefer extraction into focused modules over large helper sections.

## Epic Contract Slice

The story retains the source behavior slice and its actor/consumer boundary.

## ADR Coverage

Source references: none recorded.

## Contract Inputs

- Source story and audit-approved migration authority.
- Current epic/relationship fields in candidate frontmatter.

## Live Verification Plan

Verify the story slice through its current tasks and retain focused evidence at closeout.

## Non-Goals

No adjacent capability, terminal record, or unapproved implementation scope is added.

## Notes

### Source evidence

### Context

Several backend modules have grown into large, multi-responsibility files that are harder to reason about and test.
We need a clean refactor pass that prioritizes clarity and SRP over minimizing churn.

### Notes

- This is a refactor story: no feature behavior changes.
- Prefer extraction into focused modules over large helper sections.

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-ST-SKRIPT-06-16 | migration | closed | How is source meaning preserved? | Preserve the source story contract and current status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Story Closeout Review

No closeout evidence is asserted in this candidate.
