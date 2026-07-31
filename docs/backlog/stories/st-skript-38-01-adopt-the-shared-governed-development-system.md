---
type: story
id: ST-SKRIPT-38-01
title: Adopt the shared governed development system
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
  status: approved
  reviewer: spec-verifier
  decided_at: '2026-08-01T01:02:48+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: .orchestration/context/tasks/TASK-SKRIPT-REP-0006/reviews/spec-verifier/verify-st-skript-38-01-epic-skript-38-cutover/review.md
epic: EPIC-SKRIPT-38
acceptance_criteria:
- Given clean remote main, when the bootstrap selects the currently approved immutable
  shared-package release at execution start, then setup and governed worktree admission
  pass from the relocated checkout with exact consumer and installed identity retained
  as execution evidence.
- Given the approved corpus manifest, when migration completes, then every current
  authoritative governed document uses the common contract and every terminal backlog
  record remains historical.
- Given routine and frontend adoption, when final cutover runs, then named scopes,
  product preservation, read-only Hemma transport, staleness, handoff, and exact retirement
  pass without an unscoped aggregate.
retired_ids:
- ST-38-01
---

## Context

### Context

This repository-owned story implements Skill Repository `ST-SKILL-08-06`
without redefining its accepted cross-repository decisions.

### Slice Sequence

1. `PR-0417`: relocation and minimal package/facts walking skeleton.
2. `PR-0418`: complete governed-corpus migration and validator cutover.
3. `PR-0419`: complete bindings and topology-derived quality.
4. `PR-0420`: integrated frontend catalog/resources.
5. `PR-0421`: serial operational retirement and story proof.

### Notes

The current EPIC/ST/PR records are bootstrap authority. PR-0418 migrates their
nonterminal meaning to `TASK-SKRIPT-REP-0002` through `0006` under the common
contract. Only PR-0417 may use the approved serialized direct-`main` exception;
later slices require governed worktrees.

`TASK-SKRIPT-REP-0001` is the independently approved product-context task and
is outside this cutover. The former `TASK-SKR-REP-*` strings and
`codex/task-skr-rep-0002` proof branch remain historical planning/proof
identities only. The current PR-0418 worktree must merge current `main` before
plan review, preserve its planning changes until integration, and then be
retired without rename or reuse. After the repaired plan is approved and
integrated, the public allocator must create a new governed worktree for
`TASK-SKRIPT-REP-0003` from then-current `main`.

## Epic Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Live Verification Plan

Verification expectations remain in the retained source material below.

## Non-Goals

The source boundaries and recovery limits remain preserved below.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Story Closeout Review

- Review artifact: `.orchestration/context/tasks/TASK-SKRIPT-REP-0006/reviews/spec-verifier/verify-st-skript-38-01-epic-skript-38-cutover/review.md`
- Review decision: verified
- Reviewed checkpoint: combined `ST-SKRIPT-38-01` and sole-parent
  `EPIC-SKRIPT-38` cutover at `eecad01972a719ca8d61e73f39d853f779988eb2`
- Permitted next step: parent-owned story lifecycle transition and epic
  reconciliation
- Residual risk: the verifier review retains the non-authorizing root-level
  unit-test coverage risk; no mandatory evidence is unavailable
