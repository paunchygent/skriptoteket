---
type: task
id: TASK-SKRIPT-39-04-07
title: Keep AI answer-key suggestions on each question and request them per question
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-13'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Each question keeps its AI answer-key suggestion in the saved exam after the key is accepted
  or changed, and suggestions can be requested for one question or all keyless questions from
  the editor's current content
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Today an AI answer-key suggestion lives outside the exam, in
`exam_answer_key_proposed_overlays`. It can be requested only for the whole
saved exam, and it disappears once the teacher accepts it. TASK-SKRIPT-39-04-05
needs a suggestion that stays with its question: the Sparkles mark can restore
it after the teacher picks another option, and editing the options marks it
out of date. This task moves the suggestion onto the question and lets the
editor request suggestions for the content it is showing.

- **Suggestion on the question.** `NativeExamItem` gains an optional AI
  suggestion holding the proposed key (`correct_choice_ids`, `match_pairs` or
  gap accepted values), a fingerprint of the question's answer-relevant
  content when the suggestion was made (kind, question text, choices, gap ids,
  matches and parent instruction, as the answer-key view defines them), and
  the provider profile, model and prompt version. It is saved with the exam
  like every other item field.
- **Request.** A new request sends questions as they are in the editor, not
  the saved head:
  - "suggest for all" sends every keyed-kind question without a key;
  - the per-question action sends one question, with or without a key.

  The request creates an enrichment job that runs on that content in the
  existing execution worker with the existing provider routes, failover,
  timeout and daily token limit. The status response returns one suggestion
  per question that got a valid answer. A request works while the editor has
  unsaved changes.
- **Applying a suggestion.** The editor writes an arriving suggestion onto
  its question. When the question has no key, or its key equals its previous
  suggestion, the suggestion also becomes the key, with origin
  `machine_proposed` and review state `review_required`; any other key stays.
- **Key origins.** Marking the question reviewed turns a `machine_proposed`
  key into `reviewed_advisory`. Choosing another option makes the key
  `teacher_authored` and keeps the suggestion. Restoring the suggestion makes
  it the key again as `machine_proposed` with `review_required`. A suggestion
  whose fingerprint no longer matches the question is reported as out of
  date.
- **Removal.** Delete the overlay path in the same change, keeping no reader
  or fallback for it:
  - the `exam_answer_key_proposed_overlays` table and its model and
    repository;
  - the proposal carry-forward on save (TASK-SKRIPT-39-04-04);
  - `rejected_proposal_item_ids`;
  - the whole-head enrichment request and status routes;
  - the frontend approve, edit and reject proposal flow.

Out of scope: the editor's presentation of suggestions (TASK-SKRIPT-39-04-05),
autosave (TASK-SKRIPT-39-04-05), Mina filer exports and version pruning
(TASK-SKRIPT-39-04-08), question titles at import (TASK-SKRIPT-39-05-08) and
exam metadata (ST-SKRIPT-39-08).

## Contract Inputs

- Story: ST-SKRIPT-39-04. Retained plan: Skriptoteket session
  `01a133f5-7568-7aa9-8c03-d65722dbff09`, decisions P1-P9; editor decisions
  D32 and D42 in session `01a13061-ff38-7099-aa3d-e23f6e5bba43`.
- Item model and origins:
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`
  (answer key 169-174, origins 58-75, item 219-227).
- Answer-key view, proposal parsing and application:
  `src/skriptoteket/domain/curated_apps/exam_workspace/answer_key_view.py` and
  `answer_key_prompts.py`.
- Enrichment job, worker lane and routes:
  - `application/curated_apps/handlers/exam_workspace_enrichment.py`;
  - `exam_answer_key_enrichment_jobs.py`;
  - `exam_answer_key_enrichment_workspace_lane.py`;
  - `web/api/v1/apps_conversion_hub_exam_workspace_enrichment.py`;
  - `workers/exam_answer_key_enrichment.py`.
- To delete:
  - `exam_workspace_proposal_carry_forward.py`;
  - `domain/curated_apps/exam_workspace/proposal_carry_forward.py`;
  - the `exam_answer_key_proposed_overlay` model and repository;
  - the save request field in `application/curated_apps/exam_workspace.py`.
- Frontend:
  - `frontend/apps/skriptoteket/src/views/apps/exam-workspace/useExamWorkspaceEnrichment.ts`;
  - `useExamWorkspaceDocument.ts` (`applyProposal`);
  - `ExamWorkspaceProposalPanel.vue`;
  - `api/examWorkspace.ts`.

## Core Vertical And Performance

The core vertical: a teacher opens an exam on staging, edits a multiple-choice
question's options without saving, and requests a suggestion for that
question. The suggestion arrives, becomes the key with origin
`machine_proposed`, and the teacher marks the question reviewed. The teacher
picks another option, saves, reopens the exam and restores the AI's choice
from the saved suggestion.

Performance: a per-question request makes one provider call for that question
only. Applying suggestions must not reload or re-render the whole exam.

## Validation

- Adversarial unit tests:
  - the fingerprint changes for every answer-relevant edit and for no other
    edit;
  - a suggestion never overwrites a teacher, source or reviewed key;
  - restore and review set the stated origins;
  - "suggest for all" skips keyed questions;
  - a per-question request on unsaved content uses that content.
- Integration tests for the new request route, the job running on sent
  content, and save and reopen keeping the suggestion.
- A migration test for dropping `exam_answer_key_proposed_overlays`.
- `pdm run lint`, `pdm run typecheck` and the focused tests; `pdm run fe-test`
  and `pdm run fe-type-check` for the changed frontend files.
- A live staging walk of the core vertical, recorded in `handoff.md`.

## Stop Conditions

- The change would keep the overlay table, carry-forward or rejected-ids path
  alongside the new one.
- A provider, model, timeout or token-limit change is needed.
- The editor's suggestion presentation needs a decision that
  TASK-SKRIPT-39-04-05 has not made.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1  | This task owns only AI answer-key suggestions; Mina filer exports and version pruning, question titles at import, and exam metadata belong to TASK-SKRIPT-39-04-08, TASK-SKRIPT-39-05-08 and ST-SKRIPT-39-08 (P1, P2). |
| T2  | Each question stores its suggestion in the saved exam: the proposed key, a fingerprint of its answer-relevant content, and provider profile, model and prompt version (P5). |
| T3  | The overlay table, proposal carry-forward, `rejected_proposal_item_ids`, the whole-head enrichment routes and the frontend approve, edit and reject flow are deleted with no fallback (P5). |
| T4  | A request sends the editor's current questions and the job runs on that content in the existing worker; "suggest for all" sends keyless keyed-kind questions, the per-question action sends one question with or without a key; requests work with unsaved changes (P6). |
| T5  | An arriving suggestion becomes the key only where the question has no key or its key equals its previous suggestion, with origin `machine_proposed` and `review_required` (P8, D42). |
| T6  | Review turns `machine_proposed` into `reviewed_advisory`; choosing another option makes the key `teacher_authored`; restoring the suggestion makes it `machine_proposed` with `review_required`; a fingerprint mismatch reports the suggestion as out of date (P8, D42). |
