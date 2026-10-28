---
type: task
id: TASK-SKRIPT-REP-0055
title: The backlog matches main after the 2026-10-28 audit
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
  approval_evidence: 'Light lead (claude light-implementation-specialist 5e6a041a) applied D1-D8 on branch codex/task-skript-rep-0055, merged 817a0cf67: 24 tasks closed as done, 10 tasks and ST-21-04 canceled, 10 deferred by note and ledger row, 6 stories closed, EPIC-20 active. docs-validate and handoff-validate exit 0 after the merge. Items left open with reasons and open points are in the lead''s result (retained root 01a18449-92ba-7ada-917f-4d73cca770ab, evidence/results/5e6a041a-2c8c-4449-8318-f84a21c0ac0f.json) and per-batch evidence evidence/rep-0055/B1-B9.md; the follow-ups go to a cleanup task.'
task_kind: repository
acceptance_criteria:
  - Every item the audit classed done-on-main, stale, story-closable or deferred carries the status its decided term gives, with evidence
  - docs-validate and handoff-validate pass
backlog_document_profile: contract-derived
---

## Implementation Contract

A read-only audit on 2026-10-28 classified 186 open backlog items against main `0944a6e23`: retained root `01a1848b-76f0-787d-978c-1165be7d4b31`, file `evidence/backlog-audit-2026-10-28.md`, raw answers under `evidence/answers/`. Its evidence came from small explorers and is weak for old stories, where "0 commits" came from a grep on the story id. This task applies the audit's decided actions to the backlog docs. Before each closure it confirms the evidence in the code and history; an item whose evidence does not hold stays open and is reported.

Product code is out of scope. The two code changes the user decided (D4, D5) go to their own tasks.

## Contract Inputs

- The audit file above and its decisions section; `agent-docs-governance` lifecycle rules.

## Core Vertical And Performance

One item: read the audit row, confirm the evidence, apply the status and closeout or cancellation fields, and run docs-validate.

## Validation

- `pdm run docs-validate` and `pdm run handoff-validate` pass.
- A list of every changed item with its new status and evidence, plus every item left open with the reason.

## Stop Conditions

- An item needs a product decision the terms below do not cover. Report it; do not decide.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Close the audit's done-on-main items as `done` once their merge evidence is confirmed (approval_protocol agent-overseer:approved-review-closeout, reviewer orchestrator); 39-10-03 waits for its staging walk. 26-02-04 and REP-0022 close only with a recorded live proof; 29-11-01 closes on code because 29-11-02 owns its live proof.                                                                                                     |
| D2  | Cancel as stale: ST-21-04, 08-27-03, 11-25-01, 11-25-03, 21-01-01, 21-03-01, REP-0010, REP-0012, REP-0025 (docs-sync retirement as the recorded exception), 25-06-14 route-transport work and 25-06-08 as superseded by epic 33, and 26-02-03 (POST /rosters is the confirm path). User decision 2026-10-28 for 21-01-01, 21-03-01, 11-25-01/03, 25-06-14 and 25-06-08. Remove the stray 25-06-14 `-part-01`/`-part-02` files without status. |
| D3  | Defer 20-03-01 (user 2026-10-28) and the script-editor items 08-27-02, 08-27-04, 14-29-01, 14-32-01, 41-03-02, 41-03-03, REP-0037 and stories ST-08-08, 08-09 (user deferral of Kodredigerare work 2026-10-28). ST-41-03 stays open with its deferred tasks.                                                                                                                                                                                  |
| D4  | The Klassrumskartan share trigger reads "Dela länk" (user 2026-10-28); 26-06-01 stays open until that code change lands in its own task.                                                                                                                                                                                                                                                                                                      |
| D5  | Production startup refuses ALLOWED_HOSTS entries localhost, 127.0.0.1 and ::1 (user 2026-10-28); 09-07-01 records the decision and stays open for its implementation.                                                                                                                                                                                                                                                                         |
| D6  | Criterion fixes, then close where the rest holds: 40-04 "10-step undo" becomes "100-step" (user Q6, `MAX_RETAINED_UNDO_STEPS=100`); 40-02 closes on the Mac walk at 05b3fc12a; 25-06-02 criterion 5 points at root `handoff.md`; 25-06-04 closes as partial with the Wall34 residual moved to 25-06-03; REP-0017 criterion 2 names `http://sir_convert_a_lot_prod:8085`.                                                                      |
| D7  | Story closeout once every task is closed: ST 06-17, 06-18, 39-01, 39-04, 40-02, 40-04; ST-39-06 after 39-06-09 and ST-39-10 after 39-10-03. ST-08-36 stays open until its real clips ship (HuleFilm). EPIC-SKRIPT-20 becomes `active`; epics 22, 31, 35 and 36 stay as they are.                                                                                                                                                              |
| D8  | The audit's minor per-item questions (25-05-x, 25-06-x, 26-02-02, 20-02-02, REP-0014, 21-02-01) are decided by the orchestrator under these terms or left open and reported. Docs only, light route, no review. Orchestrator decision 2026-10-28.                                                                                                                                                                                             |
