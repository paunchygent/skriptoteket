---
type: task
id: TASK-SKRIPT-REP-0008
title: Hemma incident log findings (2026-01-04 to 2026-01-06)
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-REP-0008#closeout'
task_kind: repository
acceptance_criteria:
  - Findings from incident logs between 2026-01-04 and 2026-01-06 are documented with timestamps and log references.
  - New patterns vs prior incidents are called out (amdgpu-force-active I/O errors, AMD-Vi invalid device requests, MCE hardware errors).
  - Crash/reboot windows are summarized from journalctl list-boots output.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

## Contract Inputs

The source record did not define a separate section for this package heading.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Context

The complete migrated source is retained in these ordered parts:

- [Part 01](task-skript-rep-0008-hemma-incident-log-findings-2026-01-04-to-2026-01-06-part-01.md)
- [Part 02](task-skript-rep-0008-hemma-incident-log-findings-2026-01-04-to-2026-01-06-part-02.md)

## Impact And Escalation

Detailed content is retained in the ordered parts listed above.

## Decision And Assumption Ledger

Detailed content is retained in the ordered parts listed above.

## Plan

Detailed content is retained in the ordered parts listed above.

## Implementation Steps

Detailed content is retained in the ordered parts listed above.

## Proof

Detailed content is retained in the ordered parts listed above.

## Validation

Detailed content is retained in the ordered parts listed above.

## Stop Conditions

Detailed content is retained in the ordered parts listed above.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

Detailed content is retained in the ordered parts listed above.

## Notes

Detailed content is retained in the ordered parts listed above.

## Readiness

Detailed content is retained in the ordered parts listed above.

## Closeout

Detailed content is retained in the ordered parts listed above.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

The Hemma incident findings for 2026-01-04 to 2026-01-06 were written in 312bd998d as PR-0006 and migrated into the REP-0008 task parts in 7d2056de1. Part 01 lists the nine boot windows from journalctl list-boots and a per-crash correlation with the incident capture files; part 02 lists the new signals (amdgpu-force-active I/O errors, AMD-Vi invalid device requests, MCE hardware errors) and the continuing ones, with log file names and timestamps. The three acceptance criteria are all met by this text; no code or manual proof is involved.
