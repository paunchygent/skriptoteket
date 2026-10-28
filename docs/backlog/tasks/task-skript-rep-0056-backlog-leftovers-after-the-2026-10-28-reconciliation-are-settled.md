---
type: task
id: TASK-SKRIPT-REP-0056
title: Backlog leftovers after the 2026-10-28 reconciliation are settled
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-28'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Light lead (claude light-implementation-specialist 7de6c770, resumed as 28d5c035 after a host SSH drop) applied D1-D9 in 347ed7e33 (merged 835836194): 25-06-07 and 25-06-09 canceled; 20-02-01 done without the seriousness criterion; ADR-SKRIPT-0055 deprecated with a Rejection section (the ADR status set has no rejected); REP-0017 criterion 2 corrected; ST-14-33 and ST-20-01 done, ST-21-01 and ST-21-03 canceled; canceled children marked in place; ST-39-06 P3/P22 and 39-06-05 updated; REP-0010 guidance and skriptoteketMetadata.ts name /work/request.json; 37-05-02/03 ready and 37-05-04..06 name their blocker. docs-validate and handoff-validate exit 0; the skriptoteketCompletions spec passes 3/3. Items left as they are, with reasons, are in the lead''s result (retained root 01a18449-92ba-7ada-917f-4d73cca770ab, evidence/results/28d5c035-8bc2-409b-b17f-a987ea55480d.json): REP-0017 criteria 3-6, ST-02-06 criteria 1/2/5/6 and EPIC-40 stay open.'
task_kind: repository
acceptance_criteria:
  - Every leftover the REP-0055 report named carries the status or text its decided term gives, and docs-validate passes
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-REP-0055 (done, 170d1a405) left items its terms did not cover; its lead listed them in its result (retained root `01a18449-92ba-7ada-917f-4d73cca770ab`, `evidence/results/5e6a041a-2c8c-4449-8318-f84a21c0ac0f.json`, sections "Left open, with reasons" and "Open points for you"). This task settles them with the terms below. Each item is checked against main before its status changes; an item whose evidence does not support its term stays as it is and is reported with the reason.

Out of scope: REP-0024 and 27-09-04 (an open review with changes requested; repaired in their own task), 26-06-01 and 09-07-01 (their code fixes run now), ST-39-06, ST-39-10, ST-41-03 and ST-08-36.

## Contract Inputs

- The REP-0055 result above and the audit file in retained root `01a1848b-76f0-787d-978c-1165be7d4b31`, `evidence/backlog-audit-2026-10-28.md`.
- `agent-docs-governance` lifecycle rules.

## Core Vertical And Performance

One item: read the leftover, confirm it on main, apply its term and run docs-validate. Performance is not material.

## Validation

- `pdm run docs-validate` and `pdm run handoff-validate` pass.
- A list of every changed item with its new status or text, and every item left as it is with the reason.

## Stop Conditions

- An item needs a product decision the terms below do not cover. Report it; do not decide.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | 25-06-09 and 25-06-07 are canceled: each exists only to prove or review the canceled 25-06-08 (user decision 2026-10-28).                                                                                                                                              |
| D2  | 20-02-01 drops its criterion on a teacher-confirmed seriousness rating, which no field supports; the task closes as done if its other criteria hold on main, and otherwise stays open with the unmet criteria named (user decision 2026-10-28).                        |
| D3  | ADR-SKRIPT-0055 is rejected, with the canceled 08-27-03 as the reason (user decision 2026-10-28).                                                                                                                                                                      |
| D4  | REP-0017 criterion 2 names the Sir Convert-a-Lot address that main's `compose.dev.yaml`, `.env.example` and runbook use, `http://host.docker.internal:28085`; then the task closes if its criteria hold (orchestrator decision 2026-10-28).                            |
| D5  | ST-21-01, ST-21-03, ST-02-06, ST-14-33, ST-20-01 and EPIC-SKRIPT-40 have no open child: each closes as done when its acceptance holds on main, as canceled when every child was canceled, and otherwise stays open with the reason (orchestrator decision 2026-10-28). |
| D6  | Story and epic bodies that list canceled children mark each as canceled in place; no link is deleted (orchestrator decision 2026-10-28).                                                                                                                               |
| D7  | ST-SKRIPT-39-06: P22 and task 39-06-05 P3 read 100 undo steps; P3 notes that TASK-SKRIPT-39-06-11 allows ordering inside a part at 1 point (user decision 2026-10-28), and its task list names 39-06-11 (orchestrator decision 2026-10-28).                            |
| D8  | REP-0010's stale guidance is corrected: `stakeholders/guide-teacher-developers.md:159` and the matching text at `skriptoteketMetadata.ts:58` stop telling scripts to read `SKRIPTOTEKET_INPUTS` and name what main provides (orchestrator decision 2026-10-28).        |
| D9  | 37-05-02 to 37-05-06 name their blocker, or become ready when none exists on main; 25-06-14's part files stay (orchestrator decision 2026-10-28).                                                                                                                      |
