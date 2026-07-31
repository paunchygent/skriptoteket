---
type: task
id: TASK-SKRIPT-REP-0006
title: ST-38-01 Cut over governed development operations
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: blocked
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Installed-package routine commands, named scopes, current corpus, frontend cohort,
  read-only Hemma transport, deterministic staleness, and current handoff routing
  pass together.
- Only exact parity-proven shared-workflow overlaps retire; product, native-library,
  deployment, observability, database, migration, worker, auth/Gateway, and lower-level
  producer behavior remains.
dependencies:
- TASK-SKRIPT-REP-0005
- ST-SKRIPT-38-01
---

## Context

### Source: Problem

Final operational truth and retirements must wait until every producer and
consumer prerequisite is integrated and reviewed.

## Impact And Escalation

This is a repository-governance task; no product behavior is authorized by this task.

## Decision And Assumption Ledger

### Source: TASK-SKRIPT-REP-0006 admission ledger

This PR remains blocked until the parent closes every row with
authority-backed evidence. No implementation may infer a missing value, widen
the write set, or retire a surface while a row is open.

| ID | Closure gate | Required closure evidence |
| --- | --- | --- |
| SKR-REP-0005-01 | Exact retirement and preservation manifest | One authority-approved, file- and surface-level manifest names every shared-workflow overlap to retire, every product/native-library/deployment/observability/database/migration/worker/auth-Gateway/lower-level-producer surface to preserve, the bounded tracked-file write set, and positive parity/regression proof for each retirement. No alias, wrapper, shim, fallback, or absence-pinning test is admitted. |
| SKR-REP-0005-02 | Installed parity identities | The immutable repository-governance package release and revision, consumer facts/bindings identity, installed entrypoint paths, and disposable governed-worktree identity are recorded together. Proof runs through installed public commands and a disposable real checkout, never a package source checkout. |
| SKR-REP-0005-03 | Named final proof scopes | `check --plan` is retained before execution; the complete plan is reconciled, and the final backend/frontend/product/native regression commands are listed by accepted scope name and exact argv. Only those names run; no unscoped aggregate is permitted. |
| SKR-REP-0005-04 | Read-only Hemma facts | The approved Hemma root, remote/revision/branch, clean-state result, transport invocation, and read-only result are captured as facts. The proof performs no deploy, restart, mutation, or live-stack operation. |
| SKR-REP-0005-05 | Deterministic staleness protocol | The staleness profile, immutable source Git revision, command identity, disposition inputs, and report paths are recorded; two consecutive read-only reports are byte-identical and leave the repository diff unchanged. Historical validation remains read-only and historical-only. |
| SKR-REP-0005-06 | Root handoff and active-route criteria | Root `handoff.md` is the active handoff authority, its current route and next action are reconciled, and an audit proves every active docs/runbook/skill route reaches the root handoff. Remaining deprecated or historical pointers are classified and excluded from active routing. |
| SKR-REP-0005-07 | Dependencies reviewed and terminal | Every declared dependency (`TASK-SKRIPT-REP-0005` and `TASK-SKILL-08-06-02`) is terminal with an approved closeout review and evidence available to this slice. Missing, nonterminal, changes-requested, or stale prerequisite evidence stops admission. |

## Plan

### Source: Implementation plan

Freeze the exact retirement/preservation list, prove package parity, configure
read-only Hemma facts and staleness, move the active handoff to root with every
active route aligned, retire exact overlaps, and run the unchanged story proof.

## Implementation Steps

The source does not provide separate implementation steps.

## Proof

### Source: Test plan

Installed-package disposable-worktree proof, `check --plan`, only approved named
scopes, frontend proof, product/native regression proof, real read-only Hemma,
two deterministic staleness reports, current/historical docs validation,
handoff validation, route audit, and diff check. No unscoped aggregate.

## Validation

### Source: Test plan

Installed-package disposable-worktree proof, `check --plan`, only approved named
scopes, frontend proof, product/native regression proof, real read-only Hemma,
two deterministic staleness reports, current/historical docs validation,
handoff validation, route audit, and diff check. No unscoped aggregate.

## Stop Conditions

### Source: Stop conditions

- Any prerequisite is nonterminal or lacks approved review.
- A retirement lacks parity or affects a product-owned surface.
- Proof assumes a package source checkout, mutating Hemma, or an unscoped
  repository suite.

## Lessons Learned

The source does not record separate lessons learned.

## Notes

### Source: Rollback plan

Restore retired local surfaces and handoff routing only if parity fails before
integration; after integration use a governed forward repair.

## Readiness

The source does not include a separate readiness record.

## Closeout

The source does not include a separate closeout record.
