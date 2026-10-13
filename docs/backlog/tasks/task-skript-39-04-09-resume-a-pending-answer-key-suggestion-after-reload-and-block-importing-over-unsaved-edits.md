---
type: task
id: TASK-SKRIPT-39-04-09
title: Resume a pending answer-key suggestion after reload and block importing over unsaved edits
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-13'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A suggestion requested for the open exam's saved version reaches the exam after a reload or reopen, and no file can be imported while the open exam has unsaved changes
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The residual-risk walk on staging (2026-10-13, main 838baea9) found three
defects in the exam workspace:

- a suggestion requested just before a reload is lost: the job succeeds on
  the server, but the reloaded page never asks for it, because only the
  page that made the request holds the job id;
- importing a file while the open exam has unsaved changes discards them
  silently: the file input is disabled only while the page is busy, and the
  line "Spara det öppna provet innan du importerar ett annat." is only shown;
- the worker logs DOCX imports as "Answer-key enrichment job claimed" and
  "finished", so imports and suggestions cannot be told apart;
- a gap-fill suggestion answered the wrong label. For "Kingdom of
  mushrooms: \_\_\_ Domain of bacteria: \_\_\_" it suggested "Eukarya". The
  request squeezes both pairs onto one line and sends each gap as a bare
  number, so the model reads gap 1 as the domain. 19 of 30
  production-identical requests were right; with each gap carrying its
  label, 30 of 30 were.

This task fixes all four.

- **Finding a lost job.** The server gains an owner-only lookup that returns
  the latest suggestion job requested for an exam lineage against its
  current saved version, with the same state and suggestions as the job
  status route.

- **Resume on open.** Whenever the workspace opens an exam (reload, reopen
  from the list, switching back), it asks for that job:

  - a queued or running job is polled as if this page had requested it;
  - a finished job's suggestions are applied under 39-04-07's T5, P12 and
    P13 rules, through the same arrival path, with the lineage and
    generation check of 39-04-07 repair 4.

  A job requested for an older saved version never applies.

- **No duplicate job.** Föreslå facit, for all keyless questions or for one
  question, returns the queued or running job that already covers the same
  saved version and the same questions, instead of starting another model
  call.

- **Blocked import.** While the open exam has unsaved changes the file
  picker is disabled and dropped files are ignored. One rule decides this
  for both paths, and the existing line explains why.

- **Gap labels in suggestion requests.** Each gap sent to the suggestion
  model carries the text printed before its marker, taken from the
  existing numbered cloze text. The answer-key view, its cloze text and the
  suggestion fingerprint stay unchanged, so no stored suggestion becomes out
  of date. The DigiExam lane squeezes whitespace the same way
  (`digiexam_answer_key_prompts.py:246`); the lead checks whether it sends
  gaps without labels and fixes it the same way if so.

- **Log events.** The worker's claimed and finished events name the job's
  source kind (`docx_import`, `workspace`, `dxe`), in wording that fits
  every kind.

Out of scope: DOCX import quality
(TASK-SKRIPT-39-05-08), and the editor's presentation of suggestions
(TASK-SKRIPT-39-04-05).

## Contract Inputs

- TASK-SKRIPT-39-04-07 (done, main 838baea9): T5, P12 and P13 arrival rules;
  repair 4's rule that an arrival is written only to the lineage and
  generation that requested it, checked when it is written.
- Walk evidence: `evidence/staging-walk-838baea9/README.md`, section
  "Residual-risk walk", in retained session
  `01a133f5-7568-7aa9-8c03-d65722dbff09`.
- Current code:
  - `useExamWorkspaceEnrichment.ts:57-64` holds the job only in memory;
  - the routes in `apps_conversion_hub_exam_workspace_enrichment.py:40-71`
    take a job id only;
  - the handler `exam_workspace_enrichment.py:113-156` always creates a new
    job;
  - `ExamWorkspaceFilesMode.vue:95-102` disables the input only for
    `isBusy`;
  - `useExamWorkspaceSourceFile.ts` and `useExamWorkspaceConversion.ts:342`
    do not check unsaved changes;
  - `workers/exam_answer_key_enrichment.py:87-92` and `113-118` emit the
    log events.
- Suggestion accuracy evidence: `evidence/suggestion-accuracy/README.md`
  in retained session `01a13559-bf2e-760d-a690-3a3dea446cd5`. The squeeze
  happens at `answer_key_view.py:171`, the bare gap entries at
  `answer_key_prompts.py:187`, and reasoning effort is `low`
  (`config.py:331`).
- The repository has a unique index on `(workspace_lineage_id, workspace_document_revision)` for enrichment jobs
  (`exam_answer_key_enrichment_job.py:31-36`). Staging nevertheless ran
  several suggestion jobs against one saved version. The lead establishes
  what that column holds before choosing the lookup.

## Core Vertical And Performance

One vertical:

1. The teacher clicks Föreslå facit on a saved exam with a keyless question.
2. The teacher reloads before the result arrives.
3. The reopened exam shows the suggestion on that question, with the
   unsaved mark, exactly as if no reload had happened.

The lookup adds one indexed query to each exam open, and nothing to the
cost of a suggestion.

## Validation

- `pdm run lint` and `pdm run typecheck`.
- Focused pytest for the lookup route, the handler, the reuse rule and the
  repository query.
- Vitest for resume on open, the older-version guard, the blocked picker
  and drop, and the arrival rules after resume.
- `pdm run fe-type-check`, `pdm run fe-lint` and the frontend build.
- Staging walk on Hemma after merge:
  1. Request a suggestion, then reload within a second; the suggestion
     arrives.
  2. Request a suggestion, then open another exam and come back; the
     suggestion arrives on the first exam only.
  3. Request, save, then reload; the old job does not apply.
  4. With unsaved changes, the picker is disabled and a drop does nothing.
  5. The worker log names `docx_import` for an import.
  6. Empty both gaps of biology question 10 and request a suggestion; it
     gives Fungi and Bacteria.
- A replay of the production gap-fill request with gap labels, run against
  the real provider, scores at least 29 of 30.

## Stop Conditions

- The arrival rules of TASK-SKRIPT-39-04-07 would need to change.
- The lookup needs a schema migration that changes existing job rows.
- Any case where the contract does not say whether a resumed suggestion
  applies.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                 |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | A suggestion job the page lost track of is found again when the exam opens: the latest job requested for the exam's current saved version. A queued or running job is polled; a finished job's suggestions are applied under TASK-SKRIPT-39-04-07's T5, P12 and P13 rules (user decision 2026-10-13). |
| P2  | A job requested for an older saved version never applies once the exam has been saved again (user decision 2026-10-13).                                                                                                                                                                               |
| P3  | Föreslå facit while a job for the same saved version and the same questions is queued or running returns that job, and no second model call starts (user decision 2026-10-13).                                                                                                                        |
| P4  | While the open exam has unsaved changes, importing is impossible: the picker is disabled and drops are ignored by one shared rule, and the existing line explains why (user decision 2026-10-13).                                                                                                     |
| P5  | The worker's claimed and finished events name the job's source kind.                                                                                                                                                                                                                                  |
| P6  | Each gap sent to the suggestion model carries the text printed before its marker; the answer-key view, its cloze text and the fingerprint stay unchanged (defect found 2026-10-13, user instruction to fix every observed cause).                                                                     |
| P7  | A resumed job, once found on open, delivers across a later save like any job this page requested; P2 bounds only the lookup when the exam opens (user decision 2026-10-13).                                                                                                                           |
| P8  | A progressive-conversion batch save is a new saved version: a job requested before it is not resumed after a reload (user decision 2026-10-13).                                                                                                                                                       |
