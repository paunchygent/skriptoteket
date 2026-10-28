---
type: task
id: TASK-SKRIPT-41-02-07
title: A guest exam draft is claimed once by draft id and refused to any other teacher
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
  approval_evidence: 'D4 light proof without review: 82c381429 merged; other-teacher and concurrency tests fail before the change; focused unit 12 passed, Docker claim and migration f2b9c4d8a701 tests 5 passed, ExamWorkspaceTeacherHost spec 11 passed, rerun by the orchestrator on Hemma 2026-10-28.'
task_kind: story
acceptance_criteria:
  - The server records the guest-draft handover claim per draft_id alone; a second handover of the same draft_id by another teacher gets a 4xx whose body never reveals the first teacher's exam
  - The same teacher repeating the handover of a draft they already claimed gets the same exam back, as today
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

A guest who edits an exam and then signs in hands the browser draft over to Mina filer (TASK-SKRIPT-41-02-05). The server claims each handover per `(owner, draft_id)`. Suppose the first teacher's POST succeeded but its answer never reached the browser (network loss, an aborted request). The browser then keeps the draft, and a second teacher who signs in on the same browser can import the same draft again. This task keys the claim on `draft_id` alone.

- **First claim.** The first teacher's handover claims the draft and creates the exam, as today.
- **Same teacher again.** A repeated handover by the teacher who already claimed it returns that teacher's existing exam, as today. It creates no second copy.
- **Another teacher.** A handover of the same `draft_id` by any other teacher gets a 409. Its message tells the teacher the draft has already been saved by another account and reveals nothing about the first teacher's exam: no title, id or content. The browser then shows the existing rejected-draft notice from 41-02-05, which keeps the local draft for download or removal and records the refusal so the draft is not posted again.
- **Non-goals.** D10 (pictures in the download) is not part of this task. Guest editing does not change.

## Contract Inputs

- TASK-SKRIPT-41-02-05 term D24 and its rejected-draft notice; protocol `src/skriptoteket/protocols/exam_workspace_guest_drafts.py` and its handler, repository and migration.

## Core Vertical And Performance

One handover request: a teacher posts a guest draft, the server looks up the claim by `draft_id`, and either creates the exam, returns the same teacher's exam, or refuses with 409. The claim is one indexed row per `draft_id`; the uniqueness is enforced by the database, so two concurrent handovers cannot both win.

## Validation

- A focused backend test for each case: first claim, same-teacher repeat, other-teacher refusal with a body that carries no exam data, and two concurrent claims where exactly one wins. The other-teacher and concurrency tests fail before the change.
- The migration test for the changed uniqueness.
- A focused frontend spec showing that the 409 leads to the existing rejected-draft notice.

## Stop Conditions

- The same-teacher repeat does not return the existing exam today. Report it, because then the change has a different baseline.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The handover claim is keyed on `draft_id` alone with a database uniqueness constraint; the first teacher's handover wins (41-02-05 D24).                                                                                                       |
| D2  | A repeat by the claiming teacher returns that teacher's existing exam; another teacher gets a 409 whose body reveals nothing of the first exam, and the browser shows the existing rejected-draft notice.                                      |
| D3  | No compatibility path for the old per-owner claim rows: the migration changes the constraint, and existing development rows are not preserved.                                                                                                 |
| D4  | Proof is focused backend, migration and frontend tests; one independent review at most, repairs admitted on focused proof; no staging walk, because no screen changes. Orchestrator decision 2026-10-28 under the user's priority order (#16). |
