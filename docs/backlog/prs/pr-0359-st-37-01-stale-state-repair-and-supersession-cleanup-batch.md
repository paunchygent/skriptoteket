---
type: pr
id: PR-0359
title: "ST-37-01 stale-state repair and supersession cleanup batch"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
stories:
  - "ST-37-01"
tags:
  - docs
  - backlog
dependencies:
  - "PR-0358"
acceptance_criteria:
  - "Given `PR-0358` has produced an approved classification matrix, when this cleanup batch runs, then the touched backlog items have statuses updated only where the matrix gives evidence-backed done, canceled, dropped, or rehome decisions."
  - "Given a story is marked `done`, when its state changes, then the parent epic receives an implementation-summary update that explains the closeout."
  - "Given an item is canceled or an epic is dropped, when its state changes, then the doc names the superseding story, PR, ADR, reference, or product-direction reason."
---

# PR-0359: ST-37-01 Stale-State Repair And Supersession Cleanup Batch

## Problem

After the classification matrix exists, the docs will still lie until stale
statuses are repaired.

## Goal

Apply the first evidence-backed cleanup batch to stale backlog items.

## Non-goals

- No UI/API implementation.
- No cleanup for rows that remain `needs-decision`.
- No destructive deletion of historical records.

## Implementation plan

1. Start from the `PR-0358` matrix and choose a coherent cleanup batch.
2. Repair `done` items with evidence and parent epic summaries.
3. Mark obsolete stories/PRs `canceled` with supersession rationale.
4. Mark obsolete epics `dropped` only when the retained rationale is explicit.
5. Update `docs/index.md` and `.codex/handoff.md` for changed canonical
   surfaces.

## Implementation Summary

- Done-state repairs applied:
  - `EPIC-30` -> `done`
  - `ST-21-05` -> `done`
  - `ST-21-06` -> `done`
  - `PR-0325` -> `done`
  - `ST-14-24` -> `done`
  - `ST-14-36` -> `done`
  - `ST-14-38` -> `done`
  - `PR-0053`, `PR-0054`, `PR-0055`, `PR-0056`, `PR-0058` -> `done`
- Superseded/absorbed cancellations applied:
  - `ST-02-07`, `ST-02-09`, `PR-0172` -> `canceled`
  - `PR-0324` -> `canceled`
  - `ST-14-25`, `ST-14-26`, `ST-14-27`, `ST-14-28` -> `canceled`
  - `PR-0195`, `PR-0196`, `PR-0197` under `ST-29-11` -> `canceled`
- Parent summaries/crosslinks updated in `EPIC-02`, `EPIC-14`, `EPIC-21`,
  `EPIC-26`, `EPIC-29`, `EPIC-30`, and `ST-37-01`.
- This cleanup slice did not modify `docs/index.md` because the existing
  canonical doorway entries already cover `EPIC-37`, `PR-0358`, and `PR-0359`.

## Scope Clarifications

- `EPIC-37` remains `proposed` and `REV-EPIC-37` remains pending. This
  docs-only cleanup batch was executed on explicit 2026-06-18 implementation
  direction and does not count as epic approval or replace the retained review
  gate.
- `PR-0277` was reviewed for done-state repair but intentionally left open.
  Current docs show that the implementation shipped, yet acceptance is still
  missing the retained post-implementation review `REV-PR-0277` and a fresh
  never-before-posted Teams unfurl proof. `ST-26-07` therefore remains active.
- Red-first behavior tests are not feasible for this docs-only stale-state
  repair slice. Truthful proof comes from docs validation, handoff validation,
  and diff hygiene rather than from a red/green runtime test cycle.

## Review

- [REV-PR-0359](../reviews/review-pr-0359-stale-state-repair-and-supersession-cleanup-batch.md)
  approved this docs-only cleanup batch on 2026-06-18 with no findings.

## Test plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Verification

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the specific status changes from the batch if review finds that the
evidence does not support them.
