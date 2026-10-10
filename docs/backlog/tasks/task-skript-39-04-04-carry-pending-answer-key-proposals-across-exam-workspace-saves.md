---
type: task
id: TASK-SKRIPT-39-04-04
title: Carry pending answer-key proposals across exam workspace saves
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- An answer-key proposal the teacher has not yet approved or rejected stays available
  after the teacher saves a new version of the exam
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Answer-key proposals belong to one saved revision of an exam workspace
document. The enrichment job is looked up by owner, lineage and revision, so
when the teacher saves a new version, every proposal still waiting for a
decision disappears. The teacher then has to request proposals again, or
loses work they had not yet reviewed.

- On save, every pending proposal moves forward to the new revision, so the
  teacher sees it in the drawer exactly as before the save.
- A proposal moves forward only for an item whose answer-relevant content is
  unchanged since the proposal was made: the same kind, question text, gap
  ids and choices. A proposal for an item the teacher has changed in those
  respects is dropped as stale, because it may no longer fit the item.
- Proposals the teacher has approved or rejected are not carried; their
  outcome is already part of the saved document.
- An item deleted in the new revision drops its proposal.

## Contract Inputs

- `src/skriptoteket/infrastructure/db/models/exam_answer_key_proposed_overlay.py`
  (`ExamAnswerKeyProposedOverlayModel`, linked to a job by
  `enrichment_job_id`; stores `workspace_lineage_id` and
  `workspace_document_revision`).
- `src/skriptoteket/infrastructure/repositories/exam_answer_key_enrichment_jobs.py`
  `get_by_workspace_revision` (lines 101-112).
- `src/skriptoteket/application/curated_apps/handlers/exam_workspace_enrichment.py`
  (lookups at lines 153, 200 and 247).
- `src/skriptoteket/application/curated_apps/exam_answer_key_enrichment.py`
  (`ExamAnswerKeyProposedOverlay`, line 91).
- TASK-SKRIPT-39-04-01 (answer-key proposals) and TASK-SKRIPT-39-04-02
  (the open carry-over gate).

## Core Vertical And Performance

`request proposals -> teacher edits other items -> Spara (new version) ->
the pending proposal is still in the drawer -> approve -> save -> QTI export
holds the approved key`.

- The carry-forward runs in the save's unit of work; repositories never
  commit.
- No new LLM call and no token-lease spend on save.

## Validation

- Unit and repository tests: a pending proposal survives a save; a proposal
  for a changed item is dropped; approved and rejected proposals are not
  carried; a deleted item drops its proposal.
- Migration tests if the schema changes.
- Backend gates per `AGENTS.md`: lint, typecheck, focused tests.
- Agent-driven browser walk on Hemma staging: request proposals, save
  without deciding, reopen the drawer, approve, save, export QTI.

## Stop Conditions

- Stop if carrying proposals would require re-running enrichment or
  spending tokens on save.
- Stop if the staleness rule cannot be checked from saved item content.
- Production acceptance remains user-owned.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| P1 | Pending answer-key proposals carry over when the teacher saves a new version (user decision 2026-10-10). |
| P2 | Only proposals for items whose answer-relevant content is unchanged carry over; others are dropped as stale (user decision 2026-10-10). |
| P3 | Approved and rejected proposals are not carried; deleted items drop their proposals (user decision 2026-10-10). |
