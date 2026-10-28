---
type: story
id: ST-SKRIPT-06-17
title: Migration idempotency harness supports merge revisions
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-28'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user decided on 2026-10-28 (TASK-SKRIPT-REP-0055 D7) to close this story once all its tasks are closed: every child task is terminal. The Closeout section records the evidence.'
epic: EPIC-SKRIPT-06
acceptance_criteria:
  - tests/integration/test_migration_revision_coverage_idempotent.py passes for 6a1e9d3c4b7f and every other merge revision; migration_idempotency_support resolves a merge revision's parents instead of raising; no assertion or revision mapping is dropped.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

## Contract Inputs

## Tasks

## Verification

## Decided Contract Terms

| ID  | Decided contract term                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 because every child task is terminal (user decision, TASK-SKRIPT-REP-0055 D7). |

## Closeout

ST-SKRIPT-06-17 is closed. TASK-SKRIPT-06-17-02 (merged 3d3f867aa, test change 613fb45e3, review repairs c5c69bbb7) made `tests/integration/migration_idempotency_support.py` resolve merge-revision parents and pinned every docker migration test to its own revision; TASK-SKRIPT-06-17-01 was canceled as superseded by it (user, 2026-10-20). The merge revision 6a1e9d3c4b7f is covered and its idempotency case passed on main at 421ebd931.
