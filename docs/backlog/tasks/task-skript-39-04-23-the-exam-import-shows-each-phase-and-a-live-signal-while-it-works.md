---
type: task
id: TASK-SKRIPT-39-04-23
title: The exam import shows each phase and a live signal while it works
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-22'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Every phase of a Word or PDF import shows its name as text
  - Every phase, including the long AI waits, shows a live signal that the work is running
  - No wait during an import shows a static screen
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

A Word or PDF import into the exam workspace shows the teacher which phase is running and a live
signal that the work goes on, so no wait looks frozen.

- Today the screen shows "Konverterar provet …" with no number, then "Konverterar provet: 0 av 16
  frågor klara." unchanged for about 52 s (Word) or 3 minutes (PDF), and then every question at
  once. First-pass labelling is one AI call over all questions, and a small exam converts as one
  batch, so the count jumps from 0 to 16.
- After this task the conversion job reports its current phase and the phase's start time (D1).
  The workspace shows the phase name (D2), a moving indicator and the elapsed time of the phase
  (D3), and the question count while questions convert. The copy follows D4.
- The PDF import runs through the Word pipeline, so one change covers both.
- Non-goals: changing batch sizes, the labelling call, the AI models or the poll interval (D5); a
  cancel control; a remaining-time estimate.

## Contract Inputs

- User decision from the Mac staging walk of TASK-SKRIPT-41-01-04 at d44e946b5 (2026-10-22):
  metodprov_med_bilder.docx, 16 questions, "0 av 16 frågor klara." static for about 52 s; worker
  batch w1-01 took 57 s. The 39-04-22 PDF walk showed the same for about 3 minutes.
- Frontend: `examWorkspaceConversionStatusPoll.ts` `conversionMessage` (line 57).
- Backend: `protocols/docx_conversion_progress.py` reports only `outline` and `batch_ready`;
  `exam_workspace_docx_pipeline.py` `_label_and_convert` runs labelling and the batches; the
  status route is `web/api/v1/apps_conversion_hub_exam_workspace.py`
  (`ExamWorkspaceConversionStatus`).

## Core Vertical And Performance

The core vertical: a Word import of `metodprov_med_bilder.docx` whose status poll shows each
phase in order with a ticking elapsed time, and the count once questions convert. Reporting a
phase is one small write per phase change through the existing progress port and adds no AI call.
The elapsed time ticks in the browser, so the poll interval stays as it is.

Units, one junior each:

1. Report the phase and its start time through the progress port and the status response,
   including after a lease reclaim.
2. Show the phase text, the count, the moving indicator and the ticking elapsed time in the
   workspace, with the copy settled by one ui-copy-reviewer pass.

## Validation

- Focused backend tests: each phase is reported in order with a start time, and a reclaimed job
  reports its phase again.
- Focused frontend tests: the phase text, the count and the elapsed time that ticks each second.
- A Mac staging walk of a Word and a PDF import of `metodprov_med_bilder` in which no wait shows a
  static screen (D6).

## Stop Conditions

- Reporting a phase would need an extra AI call or a change to batching or labelling.
- The live signal would need a poll faster than today's.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                         |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The conversion job reports its current phase through the progress port, with the phase's start time: reading the file, finding the questions, sorting the questions by type (first-pass labelling) and converting the questions. A PDF import names its reading phase the same way. The status response carries the phase and its start time. |
| D2  | Every phase shows its name as text, and the converting phase adds the count "N av M frågor klara".                                                                                                                                                                                                                                            |
| D3  | Every phase shows a live signal: an existing moving indicator from the design system plus the phase's elapsed time, counted in the browser from the reported start time and updated every second. No wait shows a static screen.                                                                                                              |
| D4  | The phase copy is Swedish, short and plain, follows huleedu-ui-design, and the lead settles the exact words with one ui-copy-reviewer pass. Draft: "Läser filen", "Hittar frågorna", "Sorterar frågorna efter typ", "Konverterar frågorna: N av M klara".                                                                                     |
| D5  | Batch sizes, the labelling call, the AI models and the poll interval stay as they are. The unreleased status payload changes shape with no compatibility path.                                                                                                                                                                                |
| D6  | Proof: focused backend tests that each phase is reported in order with a start time, also after a lease reclaim; focused frontend tests of the phase text, the count and the ticking elapsed time; a Mac staging walk of a Word and a PDF import of metodprov_med_bilder in which no wait shows a static screen.                              |
| D7  | One independent review at most. Repairs are admitted on focused fail-first proof, with no rereview (user rule 2026-10-22).                                                                                                                                                                                                                    |

D1-D3 are the user's decision (relayed by the Mac orchestrator from the 41-01-04 staging walk,
2026-10-22; agent-planning:user-closure-gate). D4-D7 are orchestrator decisions under the user's
delegation (2026-10-22, "Take care of it."). All come from the retained plan in root
`01a1639c-1df3-7b78-aa2a-aca64e00aa0d`.

## Progress

- 2026-10-22, implementation on branch `codex/task-skript-39-04-23` (retained root
  `01a1639f-7d95-72f7-9140-ccb6000f8efb`). Owner: implementation lead; next: orchestrator
  review, merge and the Mac staging walk (D6).
- Backend (D1): `ConversionPhase` and `DocxConversionProgressProtocol.phase()`; the job row
  holds `conversion_phase` and `conversion_phase_started_at` (migration `aa30c309b36c`), not
  the `conversion_progress` JSON, so outline and batch merges never reset it. Reading is
  reported before the file is chunked (Word and PDF alike, also on a lease reclaim under the
  new worker), finding before grouping, sorting after the outline, converting once at the
  first labeled batch dispatch (a question no labeler sees converts at once but keeps the
  phase on sorting, so "0 av N" never sits under sorting). A stale worker's write is a no-op.
- Frontend (D2-D4): the Öppna drawer shows the phase text, the existing spinning busy glyph
  and the phase's elapsed time as m:ss, ticking each second from the reported start time
  (clamped at 0:00 against clock skew; hidden from the live region). The count shows only in
  the converting phase. A null phase (DigiExam lane, or a job still queued) keeps the old
  copy. Copy review approved; "efter typ" kept so phase 3 says what the AI does.
- Proof: lint, typecheck, backend unit 2649 passed, integration (phase, progress, migration)
  6 passed, Vitest exam-workspace and api 2743 passed. Logs in the retained root's
  `evidence/39-04-23-*.log`. Staging walk not yet done.
