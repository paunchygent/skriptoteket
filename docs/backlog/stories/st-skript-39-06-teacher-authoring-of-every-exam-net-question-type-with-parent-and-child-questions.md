---
type: story
id: ST-SKRIPT-39-06
title: Teacher authoring of every Exam.net question type with parent and child questions
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- A teacher creates any of the seven Exam.net-proven question types, as a standalone
  question or as a parent whose child questions share one instruction, and the exported
  QTI imports into Exam.net with that structure
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

A teacher builds an exam in the native workspace with every question type
that Exam.net imports and auto-marks, and decides for each task whether it is
one standalone question or a parent whose child questions share one
instruction. The exported QTI 3.0 package imports into Exam.net with exactly
that structure. Today "Ny fråga" creates free text only and the native
document has no grouping.

- **Seven question types.** Single choice, multiple choice, Lucktext (typed
  gaps), Lucktext with dropdown, matching, ordering and free text. Every type
  proven in QTI 2.1 counts as proven in QTI 3.0.
- **Standalone or parent with children.** A parent holds one shared
  instruction and one or more child questions. All children of one parent
  have the type chosen when the parent is created. Ordering questions are
  standalone only.
- **Points.** Each child has its own points; the parent shows their sum and
  is not edited directly.
- **Editing children.** Inside one parent the teacher adds, deletes and
  reorders children. Moving questions between parents, or out to standalone,
  is outside this story.
- **Teacher-facing labels follow Exam.net.** "Ny uppgift" creates a
  standalone question or a parent; "+ Deluppgift" adds a child inside a
  parent. Parent and child are internal names only.
- **Export.** Each parent exports as one QTI item: the shared instruction as
  a paragraph and one interaction per child with its own response and
  mapping; SCORE sums the children. Lucktext children keep the empty
  `SEPARATOR` gap-match element before every child sentence, a recorded
  exception to QTI 3.0 schema validity, because Exam.net imports it as
  separate child questions.
- **Conversion and gold.** DOCX conversion produces the same structure:
  section instructions become parents and their questions become children.
  TASK-SKRIPT-39-05-03 delivers this, with the gold files, the comparator,
  the native parent model, its QTI export and editor display; this story
  adds parent authoring.
- **Boundaries.** ST-SKRIPT-39-05 keeps the matching kind (native model,
  editor, QTI export) and delivers converted parents; this story adds teacher
  creation for matching and parent authoring. ST-SKRIPT-39-04's acceptance stands; creating every
  type is new scope here.

## Contract Inputs

- EPIC-SKRIPT-39 terms E3, E13, E14 and E15, and story 8 (QTI 3.0 export
  convergence), which this story follows.
- HuleEduOS `examnet-qti-import` contract
  (`.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`):
  deluppgift rules, the separator layout, and the producer's proven shapes.
- BF26 English 1 package
  (`HuleEduOS/build/exam/BF26/bf26-english1-unit-test-2026-10-02-qti3.zip`):
  the proven parent layout.
- All-types Exam.net import, 2026-10-10: Exam.net exam 5310254 "Skriptoteket
  – alla frågetyper" imported 13 tasks and 28 points from one package: six
  parents (single choice, Lucktext, Lucktext with dropdown, matching,
  multiple choice, free text) with children a) and b) and their own points,
  and seven standalone tasks including ordering. Multiple choice scored 2/2
  for the keyed answers in the grading preview.
- Current code: `NativeExamItemKind` (`native_exam_document.py:39-45`) has
  four kinds and no grouping; "Ny fråga" creates free text only
  (`useExamWorkspaceDocument.ts:386`).

## Tasks

1. Walking skeleton: on Hemma staging a teacher creates a parent with two
   Lucktext children, saves, reopens and exports QTI; the agent imports the
   package into Exam.net through the teacher's browser session and confirms
   the parent, the children and their points.
2. Remaining types as standalone questions and as parents: single choice,
   multiple choice, Lucktext with dropdown, matching (creation only; the kind
   comes from ST-SKRIPT-39-05), free text, and ordering as standalone only.
3. Child editing inside a parent: add, delete, reorder; parent points as the
   sum of its children.
4. Conversion, gold files and comparator move to parents with children
   together.

## Verification

- Each task: an agent-driven browser walk on Hemma staging, then an Exam.net
  import of the exported package through the teacher's browser session,
  checking the tasks, children, points and the grading preview.
- Story closure: one exported package holding every type, standalone and as
  parents, imports into Exam.net with the same tasks, children and points as
  the workspace showed.
- Task 4: the gold-corpus eval runs with the moved gold convention.
- Tests only on real input: real workspace documents, real exports and the
  real corpus.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| P1  | This is a new EPIC-SKRIPT-39 story sequenced after story 8, whose QTI 3.0 exporter it builds on (user decision 2026-10-10). |
| P2  | Teachers create all seven Exam.net-proven types: single choice, multiple choice, Lucktext, Lucktext with dropdown, matching, ordering, free text; every type proven in QTI 2.1 counts as proven in QTI 3.0 (user decision 2026-10-10). |
| P3  | Ordering questions are standalone only and never children of a parent (user decision 2026-10-10). |
| P4  | A question is standalone or a parent with one shared instruction and child questions; all children of a parent share the type chosen at creation (user decision 2026-10-10). |
| P5  | DOCX conversion produces the same parent and child structure: section instructions become parents and their questions become children (user decision 2026-10-10). |
| P6  | Each child has its own points; the parent shows their sum and is not edited directly (user decision 2026-10-10). |
| P7  | Inside one parent the teacher adds, deletes and reorders children; moving questions between parents or out to standalone is later work (user decision 2026-10-10). |
| P8  | The first task is the walking skeleton: a parent with two Lucktext children created, saved and exported on staging and imported into Exam.net by the agent through the teacher's browser session (user decision 2026-10-10). |
| P9  | ST-SKRIPT-39-05 task 4 keeps the matching kind; this story adds teacher creation for it (user decision 2026-10-10). |
| P10 | Superseded 2026-10-11: TASK-SKRIPT-39-05-03 moves conversion, gold and the comparator to parents (user decision 2026-10-11). |
| P11 | ST-SKRIPT-39-04's acceptance stands; creating every question type is new scope in this story (user decision 2026-10-10). |
| P12 | Lucktext children export with the empty `SEPARATOR` gap-match before every child sentence, a recorded exception to QTI 3.0 schema validity, proven by the BF26 package and the all-types import of 2026-10-10. |
| P13 | Teacher-facing labels follow Exam.net: "Ny uppgift" creates a standalone question or a parent and "+ Deluppgift" adds a child; parent and child are internal names (user confirmation 2026-10-10). |
