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
  - An answer-key proposal the teacher has not yet approved or rejected stays available after the teacher saves a new version of the exam
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
- Proposals the teacher has approved or rejected are not carried. Approved
  keys are recognised from the saved item's teacher or reviewed origin.
  Rejected proposal item IDs travel in the optional
  `SaveExamWorkspaceDocumentRequest.rejected_proposal_item_ids` field,
  which defaults to empty for older clients. They remove proposals from the
  carried overlay and are never persisted into the native document
  (parent-authorised P3 clarification, 2026-10-10).
- The frontend sends its dismissed item IDs and clears them after a
  successful save; a failed save preserves them for retry.
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

`request proposals -> teacher edits other items -> Spara (new version) -> the pending proposal is still in the drawer -> approve -> save -> QTI export holds the approved key`.

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

| ID  | Decided contract term                                                                                                                   |
| --- | --------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | Pending answer-key proposals carry over when the teacher saves a new version (user decision 2026-10-10).                                |
| P2  | Only proposals for items whose answer-relevant content is unchanged carry over; others are dropped as stale (user decision 2026-10-10). |
| P3  | Approved and rejected proposals are not carried; deleted items drop their proposals (user decision 2026-10-10).                         |

## Implementation Evidence

- 2026-10-10, branch `codex/task-skript-39-04-04`: saving copies eligible
  proposals to a new terminal, zero-attempt enrichment record and overlay
  inside the existing document-save unit of work. Old records and original
  provider/model/prompt provenance stay intact. No schema migration, LLM
  call or token-lease spend was added.
- `pdm run test-parallel` over workspace document/enrichment handler tests
  and proposal-filter domain tests, with `-n 0 -q`: 51 passed. Covers
  rejection, approval, stale/deleted items, repeated saves, older clients,
  and the saved approved key's QTI projection.
- `pdm run test-parallel tests/integration/infrastructure/repositories/test_exam_workspace_repositories.py -n 0 -q -m docker --override-ini addopts=`: 12 passed against PostgreSQL,
  including prior-revision preservation and rollback of the new document,
  overlay job, usage and stored bytes after overlay failure.
- `pdm run fe-test` over the transport, document composable, enrichment,
  save-rules, reopen, walking-skeleton and export specs: 66 passed across
  seven files. Dismissed IDs reach the save request, clear after success,
  and survive ordinary failures and same-document conflict reloads.
- `pdm run fe-gen-api-types`, `pdm run lint`, `pdm run fe-lint`,
  `pdm run fe-type-check`, and `pdm run fe-build`: passed. The build reports
  bundle-size warnings. Full `pdm run typecheck` reproduced the 12 existing
  errors in demo scripts and `tests/unit/web/test_observability_routes.py`;
  no error was reported in this task's changed files.
- Scoped `pdm run typecheck src/skriptoteket/application/curated_apps`
  and `pdm run typecheck tests/fixtures/exam_workspace_proposals.py`: passed.
- Complete command logs: retained session
  `01a1272e-5d8f-7936-b8d4-e36567440c6d`, command owner
  `01a12734-581a-7830-9782-99d89d28ee87`, captures `0010` (PostgreSQL),
  `0012` (frontend tests), `0015` (unit/domain tests), `0016` (frontend
  typecheck), `0017` (full typecheck), and `0019` (lint).
- Independent review remains parent-owned. The current assignment explicitly
  excludes the Hemma browser walk; this evidence establishes automated
  behavior and persistence, with no live-browser or production acceptance
  claim.
