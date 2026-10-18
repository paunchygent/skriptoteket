---
type: story
id: ST-SKRIPT-39-06
title: Teacher authoring of every Exam.net question type with parent and child questions
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-10"
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
  - Through the workspace API an exam holds any of six Exam.net-proven question types, with ordering added only if the user decides so after the Exam.net probe, as a standalone question or as a parent whose child questions share one instruction, and the exported QTI 3.0 package imports into Exam.net with that structure
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

An exam in the native workspace holds every question type that Exam.net
imports and auto-marks, and each task is either one standalone question or a
parent whose child questions share one instruction. The exported QTI 3.0
package imports into Exam.net with exactly that structure. Today the document
model has five item kinds and parents that only conversion creates; the
editor reads parents but cannot edit them, and "Ny fråga" offers Fritext and
Kort svar only.

- **Backend, API and export only.** This story ships the document model, the
  workspace API commands and the QTI export. Every new workspace control is
  built by ST-SKRIPT-40-04's redesign from its prototype
  (TASK-SKRIPT-40-04-01). The current workspace screens are frozen except for
  bug fixes.
- **Six question types, ordering after a probe.** Single choice, multiple
  choice, Lucktext (typed gaps), Lucktext with dropdown, matching and free
  text. Every type proven in QTI 2.1 counts as proven in QTI 3.0. An Exam.net
  probe of ordering (import, student preview, answer, grading) comes before
  any ordering build, and the user decides from its screenshots. If ordering
  is built, it is all-or-nothing with a default of 1 point that the teacher
  can edit, and it is standalone only.
- **Lucktext with dropdown.** Each gap has its own option list, and one option
  per gap is marked correct as the key.
- **Standalone or parent with children.** A parent holds one shared
  instruction and one or more child questions of any mix of types, as
  Exam.net allows.
- **Points.** Each child has its own points; the parent shows their sum and
  is not edited directly.
- **Editing children.** Workspace API commands let the teacher add, delete
  and reorder children inside one parent. TASK-SKRIPT-39-06-10 adds grouping
  questions into new parts and moving questions into, out of and between
  parts (user 2026-10-18).
- **Teacher-facing labels follow Exam.net.** "Ny uppgift" creates a
  standalone question or a parent; "+ Deluppgift" adds a child inside a
  parent. Parent and child are internal names only. These labels and their
  controls are requirements handed to ST-SKRIPT-40-04's prototype; this story
  supplies the backend behind them.
- **Export.** Each parent exports as one QTI item: the shared instruction as
  a paragraph and one interaction per child with its own response and
  mapping; SCORE sums the children. Lucktext children keep the empty
  `SEPARATOR` gap-match element before every child sentence, a recorded
  exception to QTI 3.0 schema validity, because Exam.net imports it as
  separate child questions (P12). The writer emits it in
  `exam_conversion/examnet_qti_item_xml.py` (`_append_child_body`).
- **Conversion and gold.** TASK-SKRIPT-39-05-03 has delivered DOCX conversion
  into parents and children, with the gold files, the comparator, the native
  parent model, its QTI export and its editor display. This story adds parent
  authoring.
- **Boundaries.** ST-SKRIPT-39-05 keeps the matching kind (native model,
  editor, QTI export) and delivers converted parents; this story adds teacher
  creation for matching and parent authoring. ST-SKRIPT-39-04's acceptance
  stands; creating every type is new scope here.
- **Changing a question's type.** The teacher changes any question to another
  type. The question text and points carry over; content the new type cannot
  hold is dropped, and the API names what was dropped so the workspace can
  show a notice. A type that needs structure gets the minimum empty parts (two
  empty choices, one empty gap, one empty pair), marked as blockers until
  filled; for matching the one pair holds all the points. One undo step
  restores the previous question; undo steps are the server-stored autosaves
  that TASK-SKRIPT-39-04-08 builds.
- **Suggested type.** When conversion reported that a question is of another
  type than the one it was saved as, the question stores that suggested type:
  the labeler's `retry_source.label_kind` when it differs from the saved kind.
  The workspace offers "Gör om till [type]", which converts the question to
  it through the change-type command. Asking the model to rebuild a question
  as a type the teacher chooses waits until walks show it is needed.
- **Exam.net import routes.** ST-SKRIPT-39-09 comes first: it delivers the QTI
  3.0 exporter, the Kategorisera grid, Fritext criteria, Kort svar and the
  export checklist. This story's types and parents build on them.

## Contract Inputs

- User decisions of 2026-10-17 (G2, G8, G13, G20, G23, G24, G25) and lead
  decision L1: retained root
  `.orchestration/context/sessions/01a1495e-8398-75be-b2da-f0b08ba11afa`,
  `evidence/planning/decisions-2026-10-17.md`; repository facts in
  `evidence/discovery/planning-facts-2026-10-17.md`.
- EPIC-SKRIPT-39 terms E3, E13, E14 and E15, and story 8 (QTI 3.0 export
  convergence, ST-SKRIPT-39-09), which this story follows.
- ST-SKRIPT-40-04 and TASK-SKRIPT-40-04-01: the redesign that builds every
  workspace control this story's backend serves.
- TASK-SKRIPT-39-04-08: server-stored autosaves, which are the undo steps the
  change-type command relies on (G13).
- HuleEduOS `examnet-qti-import` contract
  (`.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`):
  deluppgift rules, the separator layout, and the producer's proven shapes,
  including `qti-inline-choice-interaction` (keyed `fillGaps` with a
  selectable gap) and `qti-order-interaction` (probe round 11).
- BF26 English 1 package
  (`HuleEduOS/build/exam/BF26/bf26-english1-unit-test-2026-10-02-qti3.zip`):
  the proven parent layout.
- All-types Exam.net import, 2026-10-10: Exam.net exam 5310254 "Skriptoteket
  – alla frågetyper" imported 13 tasks and 28 points from one package: six
  parents (single choice, Lucktext, Lucktext with dropdown, matching,
  multiple choice, free text) with children a) and b) and their own points,
  and seven standalone tasks including ordering. Multiple choice scored 2/2
  for the keyed answers in the grading preview; no other grading was checked.
- `REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type`: Exam.net
  QTI 3.0 import behaviour per question type (probe rounds 13-18). Ordering
  imports as Matcha ihop with position numbers 1..N in the right column and one
  ALL_CORRECT rule (V60-V65); student view and marking were not observed.
- Current code under `src/skriptoteket/domain/curated_apps/exam_workspace/`:
  `NativeExamItemKind` (`native_exam_vocabulary.py:26`) has five kinds (free
  text, single choice, multiple response, gap fill, matching); `NativeGap`
  (`native_exam_values.py:43`) holds typed accepted values only;
  `NativeExamParent`, `validate_parent_structure` and `parent_points`
  (`native_exam_parent.py`) on `native_exam_document_v4`;
  `retry_source.label_kind` (`native_exam_retry_records.py:132`). The QTI
  writer knows five interactions (`exam_conversion/examnet_qti_contracts.py:38`).
  The only document write route is the whole-document PUT
  (`SaveExamWorkspaceDocumentHandler`). The editor reads parents only
  (`examWorkspaceParents.ts`), and "Ny fråga" offers Fritext and Kort svar
  (`ExamWorkspaceQuestionList.vue:25`).

## Tasks

Every task ships backend, API or export work only (P18); none adds a
workspace control.

1. TASK-SKRIPT-39-06-01 (backend, API, export). Walking skeleton: a parent
   with two Lucktext children saved through the workspace API, exported as
   QTI 3.0 and imported into Exam.net through the teacher's browser.
2. TASK-SKRIPT-39-06-02 (export probe). Exam.net probe of ordering and
   dropdown Lucktext: import, student preview, answer and grading, with
   retained screenshots; the user decides from them whether ordering is built.
3. TASK-SKRIPT-39-06-03 (backend, API). Parent and child commands: create a
   parent, add, delete and reorder children; parent points stay the sum of
   its children.
4. TASK-SKRIPT-39-06-04 (backend, API, export). Dropdown Lucktext kind with an
   option list per gap and one correct option, and its QTI writer. Follows the
   probe in order; it is not gated on the probe.
5. TASK-SKRIPT-39-06-05 (backend, API). Change a question's type: text and
   points carry over, dropped content is named, and one undo step restores
   the previous question.
6. TASK-SKRIPT-39-06-06 (backend, API). Stored suggested type on converted
   questions, consumed by a change to that type.
7. TASK-SKRIPT-39-06-07 (backend, API). Delete an instruction: heading only
   by default, heading with its questions as a separate command, the last
   question's delete takes the empty heading with it; every delete is one
   undo step (user 2026-10-17).

The user decided on 2026-10-18, after TASK-SKRIPT-39-06-02, to build ordering;
it joins this story as TASK-SKRIPT-39-06-08, carrying P3 and P21.

10. TASK-SKRIPT-39-06-10 (backend, API, export, workspace controls). Group
    marked questions into a new part, add an empty part, move a question into,
    out of and between parts; a part with no questions exports as an Exam.net
    information block and the last question's delete keeps the part (user
    2026-10-18; replaces TASK-SKRIPT-39-06-07 D5).

## Verification

- Each code task: on Hemma staging, the agent builds or changes the document
  through the workspace API, exports the QTI 3.0 package and imports it into
  Exam.net through the teacher's browser session, checking the tasks,
  children, points and the grading preview. Screenshots are retained in the
  retained root's `evidence/`.
- TASK-SKRIPT-39-06-02: the retained screenshots of import, student preview,
  answer and grading, and the user's recorded decision on ordering.
- Story closure: one exported package holding every built type, standalone
  and as parents, imports into Exam.net with the same tasks, children and
  points as the saved document holds.
- Tests only on real input: real workspace documents, real exports and the
  real corpus.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P1  | This is a new EPIC-SKRIPT-39 story sequenced after story 8, whose QTI 3.0 exporter it builds on (user decision 2026-10-10).                                                                                                                                                                                                                                                                                        |
| P2  | Teachers create six Exam.net-proven types: single choice, multiple choice, Lucktext, Lucktext with dropdown, matching and free text; ordering waits for the Exam.net probe of P21; every type proven in QTI 2.1 counts as proven in QTI 3.0 (user decision 2026-10-10, amended 2026-10-17 G24).                                                                                                                    |
| P3  | Ordering questions are standalone only and never children of a parent (user decision 2026-10-10).                                                                                                                                                                                                                                                                                                                  |
| P4  | A question is standalone or a parent with one shared instruction and child questions of any mix of types (user decisions 2026-10-10 and 2026-10-11).                                                                                                                                                                                                                                                               |
| P5  | DOCX conversion produces the same parent and child structure: section instructions become parents and their questions become children (user decision 2026-10-10).                                                                                                                                                                                                                                                  |
| P6  | Each child has its own points; the parent shows their sum and is not edited directly (user decision 2026-10-10).                                                                                                                                                                                                                                                                                                   |
| P7  | Inside one parent the teacher adds, deletes and reorders children; moving questions between parents or out to standalone is later work (user decision 2026-10-10); reversed 2026-10-18 by TASK-SKRIPT-39-06-10.                                                                                                                                                                                                    |
| P8  | The first task is the walking skeleton: a parent with two Lucktext children built through the workspace API, exported as QTI 3.0 and imported into Exam.net through the teacher's browser; the editor UI comes from ST-SKRIPT-40-04 (user decision 2026-10-10, amended 2026-10-17 G2).                                                                                                                             |
| P9  | ST-SKRIPT-39-05 task 4 keeps the matching kind; this story adds teacher creation for it (user decision 2026-10-10).                                                                                                                                                                                                                                                                                                |
| P11 | ST-SKRIPT-39-04's acceptance stands; creating every question type is new scope in this story (user decision 2026-10-10).                                                                                                                                                                                                                                                                                           |
| P12 | Lucktext children export with the empty `SEPARATOR` gap-match before every child sentence, a recorded exception to QTI 3.0 schema validity, proven by the BF26 package and the all-types import of 2026-10-10.                                                                                                                                                                                                     |
| P13 | Teacher-facing labels follow Exam.net: "Ny uppgift" creates a standalone question or a parent and "+ Deluppgift" adds a child; parent and child are internal names; the labels and their controls are requirements handed to ST-SKRIPT-40-04's prototype, and this story supplies the backend (user confirmation 2026-10-10, amended 2026-10-17 G2).                                                               |
| P14 | The teacher can change any question to another type; this story supplies the change-type command and ST-SKRIPT-40-04's prototype the control (user decision 2026-10-13, amended 2026-10-17 G2).                                                                                                                                                                                                                    |
| P15 | When conversion reports that a question is of another type than the one it was saved as, the question stores that suggested type and "Gör om till [type]" converts the question to it; this story supplies the stored type and the conversion, and ST-SKRIPT-40-04's prototype the offer (user decision 2026-10-13, amended 2026-10-17 G2).                                                                        |
| P16 | Asking the model to rebuild a question as a type the teacher chooses waits until walks show it is needed (user decision 2026-10-13).                                                                                                                                                                                                                                                                               |
| P17 | Epic story 8 (ST-SKRIPT-39-09, QTI 3.0 native export) is delivered first; it owns the Exam.net import routes (Kategorisera grid, Fritext criteria, Kort svar, export checklist) and their terms (user decisions 2026-10-15).                                                                                                                                                                                       |
| P18 | This story ships backend, data, API and export only; every new workspace control is built by ST-SKRIPT-40-04's redesign; the current workspace screens are frozen except for bug fixes (user decisions 2026-10-17 G2 and G8); TASK-SKRIPT-39-06-10 ships its own workspace controls (user 2026-10-18).                                                                                                             |
| P19 | Changing a question's type carries over its question text and points; content the new type cannot hold is dropped with a visible notice naming it, and one undo step restores it (user decision 2026-10-17 G20).                                                                                                                                                                                                   |
| P20 | Lucktext with dropdown gives each gap its own option list with one correct option marked as the key (user decision 2026-10-17 G23).                                                                                                                                                                                                                                                                                |
| P21 | An Exam.net probe of ordering (import, student preview, answer, grading) comes before any ordering build, as TASK-SKRIPT-39-06-02; the user decides from its screenshots; until then the story plans six types; ordering is all-or-nothing with a default of 1 point that the teacher can edit (user decision 2026-10-17 G24); the user decided on 2026-10-18 to build it after the probe (Exam.net exam 5345282). |
| P22 | Undo keeps at most 10 steps; each autosave is one step, stored on the server so history survives reload and reopening (user decision 2026-10-17 G13).                                                                                                                                                                                                                                                              |
| P23 | A change into a type that needs structure carries over the text and points and gives the new type the minimum empty parts (two empty choices, one empty gap, one empty pair), marked as blockers until filled; for matching the one pair holds all the points (user 2026-10-17, G25).                                                                                                                              |
| P24 | The suggested type is the labeler's `retry_source.label_kind` when it differs from the saved kind (lead 2026-10-17, L1).                                                                                                                                                                                                                                                                                           |
