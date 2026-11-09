---
type: task
id: TASK-SKRIPT-REP-0069
title: Adopt yamllint from the shared tooling list
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-09'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-11-09T17:14:23Z'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: >-
    Independent ruthless-reviewer 36f588a5-64f0-4766-a6a5-ffcdc999e995 approved
    commit 090cd3242232d4fb75500b277105e91e7dfcadfb at 2026-11-09T17:14:23+00:00
    with no findings (retained session
    01a1be02-7ff8-7c5c-82d1-d370b5612689,
    discovery/ruthless-reviewer/36f588a5-64f0-4766-a6a5-ffcdc999e995/0001-review-three-commits-that-adopt-the-yamllint-pin-from-the.md);
    the review verified the managed tooling block adds exactly
    `yamllint==1.38.0`, preserves every existing locked package and version,
    and keeps the lock consistent with the pyproject. Both acceptance criteria
    are met: `pdm run yamllint --version` reports 1.38.0 and
    `repository-governance-bindings check` exits 0 with no drift.
task_kind: repository
acceptance_criteria:
  - '`pdm run yamllint --version` reports 1.38.0.'
  - '`repository-governance-bindings check` reports no drift.'
backlog_document_profile: contract-derived
---

## Implementation Contract

The routine lint phase runs `pdm run yamllint` on changed YAML and this
repository had none.

## Contract Inputs

## Core Vertical And Performance

## Validation

## Stop Conditions

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |

## Closeout

- Outcome: `pyproject.toml` declares `yamllint==1.38.0` inside the shared
  managed tooling block and `pdm.lock` adds yamllint 1.38.0 while preserving
  every existing package and version; reviewed commit
  `090cd3242232d4fb75500b277105e91e7dfcadfb` was approved with no findings.
- Proof: `pdm run yamllint --version` reports `yamllint 1.38.0`;
  `repository-governance-bindings check` exits 0 with no drift.
- Review record (skill-repository primary checkout):
  `.orchestration/context/sessions/01a1be02-7ff8-7c5c-82d1-d370b5612689/discovery/ruthless-reviewer/36f588a5-64f0-4766-a6a5-ffcdc999e995/0001-review-three-commits-that-adopt-the-yamllint-pin-from-the.md`.
