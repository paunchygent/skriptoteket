---
type: epic
id: EPIC-SKRIPT-38
title: Shared governed development system cutover
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User approved the complete cutover contract and execution
closeout_review:
  record: inline
  status: approved
  reviewer: spec-verifier
  decided_at: '2026-08-01T01:02:48+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: .orchestration/context/tasks/TASK-SKRIPT-REP-0006/reviews/spec-verifier/verify-st-skript-38-01-epic-skript-38-cutover/review.md
outcome: Skriptoteket uses the central repository-governance package and common Docs-as-Code
  contract while terminal backlog remains historical and product behavior remains
  locally owned.
retired_ids:
- EPIC-38
---

## Scope

### Source: Scope

- Relocate the clean checkout to
  `.`.
- Select the currently approved immutable `repository-governance` release per
  executable slice and prove the public setup/worktree/check foundation.
- Migrate every current authoritative governed document to the common contract
  through one exact disposition manifest.
- Keep terminal backlog and terminal reviews historical.
- Replace active local governed-document validation with shared current
  validation and retain any historical validator only as read-only historical
  inspection.
- Adopt topology-derived quality scopes and the central frontend cohort.
- Retire only parity-proven shared-workflow overlaps.

## Epic Contract

The epic outcome is represented by the scope and stories recorded above.

## ADR Coverage

No separate ADR coverage was recorded in the source snapshot.

## Contract Inputs

### Source: Dependencies

- Skill Repository `ST-SKILL-08-06` and its accepted SKR-001 through SKR-004P
  ledger.
- An approved immutable `repository-governance` release selected per
  executable slice, with exact identity retained as execution evidence.

## Stories

### Source: Story Stack

- [ST-SKRIPT-38-01](../stories/st-skript-38-01-adopt-the-shared-governed-development-system.md)

## Epic Verification Plan

| Gate | Verification Result | Evidence | Owner | Follow-up / Exception |
| --- | --- | --- | --- | --- |
| Complete Skriptoteket governed-development consumer cutover | verified | `.orchestration/context/tasks/TASK-SKRIPT-REP-0006/reviews/spec-verifier/verify-st-skript-38-01-epic-skript-38-cutover/review.md` | ST-SKRIPT-38-01 | None |

## Exceptions And Follow-Ups

No separate exceptions or follow-ups were recorded in the source snapshot.

## Risks

### Source: Risks

- Bulk migration without identity and lifecycle closure could promote stale
  authority or corrupt review relationships.
- A second validator or compatibility route could leave two active contracts.
- Checkout relocation could leave active machine-local paths in central or
  consumer guidance.

## Notes

No additional notes were recorded in the source snapshot.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

### Source: Review Gate

`REV-EPIC-38` must approve this consumer spine before the one-time bootstrap.

## Epic Closeout Review

- Review artifact: `.orchestration/context/tasks/TASK-SKRIPT-REP-0006/reviews/spec-verifier/verify-st-skript-38-01-epic-skript-38-cutover/review.md`
- Review decision: verified
- Reviewed checkpoint: combined `ST-SKRIPT-38-01` and `EPIC-SKRIPT-38`
  cutover at `eecad01972a719ca8d61e73f39d853f779988eb2`
- Permitted next step: parent-owned lifecycle transition and reconciliation
- Residual risk: the verifier review retains the non-authorizing root-level
  unit-test coverage risk; no mandatory evidence is unavailable
